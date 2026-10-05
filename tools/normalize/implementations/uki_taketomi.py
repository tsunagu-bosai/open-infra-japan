#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

from tools.normalize.core.normalization import RowSupport, StandardCsvWriter

ROOT = Path.cwd()
RAW = ROOT / "data/raw"
NORMALIZED = ROOT / "data/normalized"
SCHEMA = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "43213": {
        "pref_dir": "43-熊本県",
        "mun_dir": "43213-宇城市",
    },
    "47381": {
        "pref_dir": "47-沖縄県",
        "mun_dir": "47381-竹富町",
    },
}

COUNT_FIELDS = [
    "男性トイレ総数",
    "男性トイレ数（小便器）",
    "男性トイレ数（和式）",
    "男性トイレ数（洋式）",
    "女性トイレ総数",
    "女性トイレ数（和式）",
    "女性トイレ数（洋式）",
    "男女共用トイレ総数",
    "男女共用トイレ数（和式）",
    "男女共用トイレ数（洋式）",
    "バリアフリートイレ数",
]


def read_schema() -> list[str]:
    with SCHEMA.open("r", encoding="utf-8-sig", newline="") as f:
        return [r["name"] for r in csv.DictReader(f)]


def detect_encoding(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            pass
    raise RuntimeError(f"cannot decode: {path}")


def read_exact39(path: Path, schema: list[str]) -> tuple[list[dict[str, str]], str]:
    enc = detect_encoding(path)
    with path.open("r", encoding=enc, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        if header != schema:
            raise RuntimeError(
                f"{path}: source header is not exact 39-column schema "
                f"(columns={len(header)})"
            )

        rows = []
        for row in reader:
            clean = {k: (v or "").strip() for k, v in row.items()}
            if not any(clean.values()):
                continue
            rows.append(clean)
    return rows, enc



def normalize_ukishi(rows: list[dict[str, str]]) -> tuple[int, int]:
    corrected_rows = 0
    corrected_fields = 0

    for row in rows:
        values = {
            row.get("全国地方公共団体コード", ""),
            row.get("所在地_全国地方公共団体コード", ""),
        }

        bad = sorted(v for v in values if v in {
            "432131", "432132", "432133",
            "432134", "432135", "432136",
        })

        if not bad:
            continue

        corrected_rows += 1

        for field in (
            "全国地方公共団体コード",
            "所在地_全国地方公共団体コード",
        ):
            old = row.get(field, "")
            if old in {
                "432131", "432132", "432133",
                "432134", "432135", "432136",
            }:
                row[field] = "432130"
                corrected_fields += 1

        RowSupport.append_note(
            row,
            "原データ地方公共団体コード=" + ",".join(bad),
        )

    return corrected_rows, corrected_fields


def is_integer(value: str) -> bool:
    value = value.strip()
    if not value:
        return True
    try:
        int(value)
        return True
    except ValueError:
        return False


def normalize_taketomi(rows: list[dict[str, str]]) -> tuple[int, int]:
    affected_rows = 0
    corrected_values = 0

    for row in rows:
        changes: list[tuple[str, str]] = []

        for field in COUNT_FIELDS:
            value = row.get(field, "").strip()
            if not value:
                continue

            if is_integer(value):
                continue

            # Known source anomalies:
            #   女性トイレ数（洋式） = 00:00
            #   男性トイレ総数       = 解体予定
            #   数値欄               = 1？ / 2？
            if (
                value == "00:00"
                or value == "解体予定"
                or value.endswith("？")
            ):
                changes.append((field, value))
            else:
                raise RuntimeError(
                    f"竹富町: unexpected non-numeric count value "
                    f"{field}={value!r} 名称={row.get('名称','')!r}"
                )

        if not changes:
            continue

        affected_rows += 1

        for field, value in changes:
            row[field] = ""
            corrected_values += 1
            RowSupport.append_note(row, f"原データ{field}={value}")

    return affected_rows, corrected_values



def main() -> int:
    schema = read_schema()
    if len(schema) != 39:
        raise RuntimeError(f"expected 39 schema columns, got {len(schema)}")

    for code, cfg in TARGETS.items():
        raw_dir = (
            RAW
            / cfg["pref_dir"]
            / cfg["mun_dir"]
            / "public-toilet"
        )
        sources = sorted(raw_dir.glob("*.csv"))
        if len(sources) != 1:
            raise RuntimeError(
                f"{code}: expected exactly one raw CSV, got "
                + ", ".join(p.name for p in sources)
            )

        rows, enc = read_exact39(sources[0], schema)

        if not rows:
            raise RuntimeError(f"{code}: no data rows")

        if code == "43213":
            affected, changes = normalize_ukishi(rows)
        else:
            rows = [
                row for row in rows
                if (row.get("名称") or "").strip()
            ]
            affected, changes = normalize_taketomi(rows)

        out = (
            NORMALIZED
            / cfg["pref_dir"]
            / cfg["mun_dir"]
            / "public-toilet/public-toilet.csv"
        )
        StandardCsvWriter().write(out, schema, rows)

        print(
            f"{code} {cfg['mun_dir']}: "
            f"rows={len(rows)} source={sources[0].name} encoding={enc} "
            f"affected_rows={affected} corrected_values={changes}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
