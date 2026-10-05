#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

from tools.normalize.core.encoding import detect_text_encoding
from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.normalization import RowSupport, StandardCsvWriter
from tools.normalize.core.schema import read_schema_fields

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "11210": {
        "name": "加須市",
        "pref": "11-埼玉県",
        "mun": "11210-加須市",
        "file": "11210_public-toilet.csv",
        "kind": "kazo_parks",
    },
    "11219": {
        "name": "上尾市",
        "pref": "11-埼玉県",
        "mun": "11219-上尾市",
        "file": "11219_public-toilet.csv",
        "kind": "ageo_legacy",
    },
}



def read_source(path: Path) -> tuple[list[str], list[dict[str, str]], str]:
    enc = detect_text_encoding(path)
    with path.open("r", encoding=enc, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        rows: list[dict[str, str]] = []
        for line_no, source in enumerate(reader, 2):
            if None in source:
                raise RuntimeError(f"{path}:{line_no}: overflow columns={source[None]!r}")
            row = {k: RowSupport.clean(v) for k, v in source.items()}
            if any(row.values()):
                rows.append(row)
    return header, rows, enc


def base_row(schema: list[str], code: str, name: str) -> dict[str, str]:
    code6 = six_digit_municipality_code(code)
    row = {field: "" for field in schema}
    row["全国地方公共団体コード"] = code6
    row["所在地_全国地方公共団体コード"] = code6
    row["地方公共団体名"] = f"埼玉県{name}"
    row["所在地_都道府県"] = "埼玉県"
    row["所在地_市区町村"] = name
    return row


def normalize_ageo(
    source: dict[str, str],
    schema: list[str],
    code: str,
    name: str,
) -> dict[str, str]:
    row = base_row(schema, code, name)
    row["ID"] = source["NO"]
    row["名称"] = source["名称"]
    row["名称_カナ"] = source["名称_カナ"]
    row["所在地_連結表記"] = f"埼玉県{source['住所']}" if source["住所"] else ""
    row["建物名等(方書)"] = source["方書"]
    row["緯度"] = source["緯度"]
    row["経度"] = source["経度"]
    row["男性トイレ総数"] = source["男性トイレ数"]
    row["女性トイレ総数"] = source["女性トイレ数"]
    row["男女共用トイレ総数"] = source["男女共用トイレ数"]

    availability = source["利用可能時間"]
    if availability == "終日":
        row["利用開始時間"] = "00:00"
        row["利用終了時間"] = "23:59"
    elif availability:
        row["利用可能時間特記事項"] = availability

    row["備考"] = source["備考"]
    if source["トイレ箇所数"]:
        RowSupport.append_note(row, f"原データトイレ箇所数={source['トイレ箇所数']}")
    if source["多機能トイレ数"]:
        RowSupport.append_note(row, f"原データ多機能トイレ数={source['多機能トイレ数']}")
    return row


KAZO_PRESERVE_FIELDS = (
    "地区別",
    "地域",
    "種別",
    "面積（㎡）",
    "面積（ha）",
    "照明（男）",
    "うち、LED",
    "照明（女）",
    "照明（障）",
    "トイレ",
    "トイレ箇所数",
    "大便器合計",
    "障",
    "障_和",
    "障_洋",
    "小便\n器数",
    "身障\n者",
    "凍結\n防止",
)


def normalize_kazo(
    source: dict[str, str],
    schema: list[str],
    code: str,
    name: str,
) -> dict[str, str]:
    row = base_row(schema, code, name)
    row["ID"] = source["ＮＯ"]
    row["名称"] = source["公園名"]
    row["所在地_連結表記"] = (
        f"埼玉県加須市{source['公園の所在地']}"
        if source["公園の所在地"]
        else ""
    )
    row["男性トイレ総数"] = source["男"]
    row["男性トイレ数（和式）"] = source["男_和"]
    row["男性トイレ数（洋式）"] = source["男_洋"]
    row["女性トイレ総数"] = source["女"]
    row["女性トイレ数（和式）"] = source["女_和"]
    row["女性トイレ数（洋式）"] = source["女_洋"]
    row["備考"] = source["備　　考"]

    accessible = source.get("身障\n者", "")
    if accessible == "○":
        row["車椅子使用者用トイレ有無"] = "有"
    elif accessible:
        raise RuntimeError(
            f"{code}: unexpected 身障者 value={accessible!r}"
        )

    for field in KAZO_PRESERVE_FIELDS:
        value = source.get(field, "")
        if value:
            RowSupport.append_note(row, f"原データ{field.replace(chr(10), '')}={value}")
    return row


NORMALIZERS = {
    "ageo_legacy": normalize_ageo,
    "kazo_parks": normalize_kazo,
}



def main() -> None:
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    prepared = []
    for code, cfg in TARGETS.items():
        src = (
            ROOT
            / "data/raw"
            / cfg["pref"]
            / cfg["mun"]
            / "public-toilet"
            / cfg["file"]
        )
        dest = (
            ROOT
            / "data/normalized"
            / cfg["pref"]
            / cfg["mun"]
            / "public-toilet/public-toilet.csv"
        )
        if not src.exists():
            raise RuntimeError(f"{code}: raw missing: {src}")
        if dest.exists():
            raise RuntimeError(f"{code}: normalized already exists: {dest}")

        header, source_rows, enc = read_source(src)
        if not source_rows:
            raise RuntimeError(f"{code}: no data rows")

        normalizer = NORMALIZERS[cfg["kind"]]
        rows = [normalizer(source, schema, code, cfg["name"]) for source in source_rows]

        if any(not row["ID"] for row in rows):
            raise RuntimeError(f"{code}: blank ID found")
        if any(not row["名称"] for row in rows):
            raise RuntimeError(f"{code}: blank 名称 found")

        prepared.append((code, cfg["name"], dest, rows, enc, len(header)))

    print(f"preflight OK: {len(prepared)} municipalities")
    for code, name, dest, rows, enc, columns in prepared:
        StandardCsvWriter().write(dest, schema, rows)
        print(
            f"OK {code} {name}: rows={len(rows)} "
            f"encoding={enc} source_columns={columns}"
        )


if __name__ == "__main__":
    main()
