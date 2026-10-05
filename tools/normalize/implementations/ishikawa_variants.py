#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from pathlib import Path

from tools.normalize.core.encoding import detect_text_encoding
from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.normalization import (
    PreserveEndOfDayTimeStrategy,
    RowSupport,
    StandardCsvWriter,
)

ROOT = Path.cwd()
RAW = ROOT / "data/raw"
OUT = ROOT / "data/normalized"
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "17203": ("小松市", "13_172031_public_toilet.csv", "standard37"),
    "17204": ("輪島市", "172049_public_toilet.csv", "wajima36"),
    "17205": ("珠洲市", "172057_public_toilet.csv", "standard37"),
    "17324": ("川北町", "173240_public_toilet.csv", "headerless37"),
    "17384": ("志賀町", "173843_public_toilet.csv", "standard37"),
    "17386": ("宝達志水町", "173860_public_toilet.csv", "standard37"),
    "17461": ("穴水町", "174611_public_toilet.csv", "standard37"),
}

HEADER37 = [
    "全国地方公共団体コード",
    "ID",
    "都道府県名",
    "市区町村名",
    "名称",
    "名称_カナ",
    "名称_英語",
    "所在地_全国地方公共団体コード",
    "所在地_連結標記",
    "所在地_都道府県",
    "所在地_市区町村",
    "所在地_町字",
    "所在地_番地以下",
    "建物名等(方書)",
    "設置位置",
    "緯度",
    "経度",
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
    "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無",
    "利用開始時間",
    "利用終了時間",
    "利用可能時間特記事項",
    "画像",
    "画像_ライセンス",
    "備考",
]

HEADER36_WAJIMA = [
    "全国地方公共団体コード",
    "ID",
    "地方公共団体名",
    "名称",
    "名称_カナ",
    "名称_英語",
    "町字ID",
    "所在地_都道府県",
    "所在地_市区町村",
    "所在地_町字",
    "所在地_番地以下",
    "建物名等(方書)",
    "緯度",
    "経度",
    "高度の種別",
    "高度の値",
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
    "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無",
    "利用開始時間",
    "利用終了時間",
    "利用可能時間特記事項",
    "画像",
    "画像_ライセンス",
    "備考",
]

BOOL_FIELDS = (
    "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無",
)



def append_field(row: dict[str, str], field: str, text: str) -> None:
    text = RowSupport.clean(text)
    if not text:
        return
    cur = RowSupport.clean(row.get(field))
    if text in cur:
        return
    row[field] = f"{cur} / {text}" if cur else text



def normalize_bool(row: dict[str, str], field: str) -> None:
    value = RowSupport.clean(row.get(field))

    if value in ("", "有", "無"):
        return

    if value == "可":
        append_field(row, "備考", f"原データ{field}=可")
        row[field] = "有"
        return

    if value in {"否", "0"}:
        append_field(row, "備考", f"原データ{field}={value}")
        row[field] = "無"
        return

    append_field(row, "備考", f"原データ{field}={value}")
    row[field] = ""


_TIME_STRATEGY = PreserveEndOfDayTimeStrategy()


def normalize_times(row: dict[str, str]) -> None:
    start_raw = RowSupport.clean(row.get("利用開始時間"))
    end_raw = RowSupport.clean(row.get("利用終了時間"))

    # 「終日」は意味が明確なので標準時刻へ寄せ、原値を残す。
    if start_raw == "終日":
        append_field(row, "備考", "原データ利用開始時間=終日")
        row["利用開始時間"] = "00:00"
    else:
        value, preserved = _TIME_STRATEGY(start_raw)
        row["利用開始時間"] = value
        if preserved:
            append_field(row, "利用可能時間特記事項",
                         f"原データ利用開始時間={preserved}")

    if end_raw == "終日":
        append_field(row, "備考", "原データ利用終了時間=終日")
        row["利用終了時間"] = "23:59"
    else:
        value, preserved = _TIME_STRATEGY(end_raw)
        row["利用終了時間"] = value
        if preserved:
            append_field(row, "利用可能時間特記事項",
                         f"原データ利用終了時間={preserved}")


def read_rows(path: Path, kind: str) -> tuple[list[dict[str, str]], str]:
    enc = detect_text_encoding(path)

    with path.open(encoding=enc, newline="") as f:
        if kind == "headerless37":
            reader = csv.DictReader(f, fieldnames=HEADER37)
        else:
            reader = csv.DictReader(f)

        header = reader.fieldnames or []

        expected = HEADER36_WAJIMA if kind == "wajima36" else HEADER37
        if header != expected:
            raise RuntimeError(
                f"{path}: unexpected header\n"
                f"actual={header!r}\nexpected={expected!r}"
            )

        rows = []
        for line_no, source in enumerate(reader, 1 if kind == "headerless37" else 2):
            if None in source:
                raise RuntimeError(
                    f"{path}:{line_no}: overflow columns={source[None]!r}"
                )

            row = {k: RowSupport.clean(v) for k, v in source.items()}
            if not any(row.values()):
                continue
            rows.append(row)

    return rows, enc


def normalize_standard37(
    code: str,
    source: dict[str, str],
    schema: list[str],
) -> dict[str, str]:
    row = {field: "" for field in schema}

    direct = {
        "全国地方公共団体コード",
        "ID",
        "名称",
        "名称_カナ",
        "名称_英語",
        "所在地_全国地方公共団体コード",
        "所在地_都道府県",
        "所在地_市区町村",
        "所在地_町字",
        "所在地_番地以下",
        "建物名等(方書)",
        "設置位置",
        "緯度",
        "経度",
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
        "車椅子使用者用トイレ有無",
        "乳幼児用設備設置トイレ有無",
        "オストメイト設置トイレ有無",
        "利用開始時間",
        "利用終了時間",
        "利用可能時間特記事項",
        "画像",
        "画像_ライセンス",
        "備考",
    }

    for field in direct:
        row[field] = source.get(field, "")

    pref = RowSupport.clean(source.get("都道府県名"))
    municipality = RowSupport.clean(source.get("市区町村名"))
    row["地方公共団体名"] = pref + municipality
    row["所在地_連結表記"] = RowSupport.clean(source.get("所在地_連結標記"))

    # 珠洲市のIDは全29行が同一の科学表記値で、識別子として使用できない。
    if code == "17205" and re.fullmatch(
        r"\d+(?:\.\d+)?E[+-]?\d+", RowSupport.clean(row["ID"]), re.IGNORECASE
    ):
        append_field(row, "備考", f"原データID={row['ID']}")
        row["ID"] = ""

    for field in BOOL_FIELDS:
        normalize_bool(row, field)

    normalize_times(row)
    return row


def normalize_wajima(
    source: dict[str, str],
    schema: list[str],
) -> dict[str, str]:
    row = {field: "" for field in schema}

    for field in HEADER36_WAJIMA:
        if field in row:
            row[field] = source.get(field, "")

    # 原データに存在しない以下3項目は推測補完しない。
    row["所在地_全国地方公共団体コード"] = ""
    row["所在地_連結表記"] = ""
    row["設置位置"] = ""

    for field in BOOL_FIELDS:
        normalize_bool(row, field)

    normalize_times(row)
    return row



    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=schema, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    tmp.replace(path)


def prepare_one(
    code: str,
    name: str,
    filename: str,
    kind: str,
    schema: list[str],
):
    src = RAW / "17-石川県" / f"{code}-{name}" / "public-toilet" / filename
    dest = OUT / "17-石川県" / f"{code}-{name}" / "public-toilet/public-toilet.csv"

    if not src.exists():
        raise RuntimeError(f"{code}: raw missing: {src}")
    if dest.exists():
        raise RuntimeError(f"{code}: normalized already exists: {dest}")

    source_rows, enc = read_rows(src, kind)

    if not source_rows:
        raise RuntimeError(f"{code}: source contains no meaningful data rows")

    normalized = []
    for source in source_rows:
        if kind == "wajima36":
            row = normalize_wajima(source, schema)
        else:
            row = normalize_standard37(code, source, schema)
        normalized.append(row)

    return dest, enc, normalized


def main():
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    prepared = []

    for code, (name, filename, kind) in TARGETS.items():
        dest, enc, rows = prepare_one(
            code, name, filename, kind, schema
        )
        prepared.append((code, name, dest, enc, rows))

    print(f"preflight OK: {len(prepared)} municipalities")

    for code, name, dest, enc, rows in prepared:
        StandardCsvWriter().write(dest, schema, rows)
        print(f"OK {code} {name}: rows={len(rows)} encoding={enc}")


if __name__ == "__main__":
    main()
