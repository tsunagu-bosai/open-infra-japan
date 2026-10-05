#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.normalization import (
    RowSupport,
    Sha256StableIdStrategy,
    StandardCsvWriter,
)
from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.xlsx import read_xlsx_values


ROOT = Path.cwd()

SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

SOURCE = (
    ROOT
    / "data/raw/10-群馬県/10000-群馬県/public-toilet/710891.xlsx"
)

OUT_ROOT = ROOT / "data/normalized/10-群馬県"

SHEET_NAME = "取りまとめ用（R7）"

EXPECTED_HEADER = [
    "NO.",
    "所在地\n（市町村名）",
    "施設名",
    "施設の住所",
    "電話番号",
    "オストメイト対応の\n多目的トイレの位置",
    "ユニバーサルシート設置の\n多目的トイレの位置",
    "利用可能時間\n（施設の休館日除く）",
    "備考",
    "所管\n（自治体名）",
    "担当所属（所管が市町村の場合は不要）",
    "",
]

MUNICIPALITIES = [
    ("10201", "前橋市"),
    ("10202", "高崎市"),
    ("10203", "桐生市"),
    ("10204", "伊勢崎市"),
    ("10205", "太田市"),
    ("10206", "沼田市"),
    ("10207", "館林市"),
    ("10208", "渋川市"),
    ("10209", "藤岡市"),
    ("10210", "富岡市"),
    ("10211", "安中市"),
    ("10212", "みどり市"),
    ("10344", "榛東村"),
    ("10345", "吉岡町"),
    ("10366", "上野村"),
    ("10367", "神流町"),
    ("10384", "甘楽町"),
    ("10421", "中之条町"),
    ("10424", "長野原町"),
    ("10425", "嬬恋村"),
    ("10426", "草津町"),
    ("10428", "高山村"),
    ("10429", "東吾妻町"),
    ("10443", "片品村"),
    ("10444", "川場村"),
    ("10448", "昭和村"),
    ("10449", "みなかみ町"),
    ("10464", "玉村町"),
    ("10521", "板倉町"),
    ("10522", "明和町"),
    ("10524", "大泉町"),
    ("10525", "邑楽町"),
]

MUNICIPALITY_BY_NAME = {
    name: code
    for code, name in MUNICIPALITIES
}

# 中之条町は既存の自治体別データを優先する。
EXCLUDED_CODES = {"10421"}

TARGETS = [
    (code, name)
    for code, name in MUNICIPALITIES
    if code not in EXCLUDED_CODES
]

EXPECTED_COUNTS = {
    "前橋市": 56,
    "高崎市": 56,
    "桐生市": 18,
    "伊勢崎市": 25,
    "太田市": 31,
    "沼田市": 15,
    "館林市": 6,
    "渋川市": 16,
    "藤岡市": 19,
    "富岡市": 9,
    "安中市": 6,
    "みどり市": 13,
    "榛東村": 3,
    "吉岡町": 3,
    "上野村": 1,
    "神流町": 3,
    "甘楽町": 4,
    "中之条町": 9,
    "長野原町": 6,
    "嬬恋村": 5,
    "草津町": 2,
    "高山村": 2,
    "東吾妻町": 7,
    "片品村": 3,
    "川場村": 3,
    "昭和村": 1,
    "みなかみ町": 7,
    "玉村町": 3,
    "板倉町": 1,
    "明和町": 1,
    "大泉町": 1,
    "邑楽町": 4,
}

_ID_STRATEGY = Sha256StableIdStrategy()
_WRITER = StandardCsvWriter()


def main() -> None:
    if not SOURCE.exists():
        raise RuntimeError(f"missing source: {SOURCE}")

    schema = read_schema_fields(SCHEMA_PATH)

    if len(schema) != 39:
        raise RuntimeError(
            f"schema columns={len(schema)} expected=39"
        )

    values = read_xlsx_values(
        SOURCE,
        sheet_name=SHEET_NAME,
    )

    if len(values) < 3:
        raise RuntimeError("source workbook has too few rows")

    header = [
        RowSupport.clean_cell(value)
        for value in values[1]
    ]

    if header != EXPECTED_HEADER:
        raise RuntimeError(
            f"source header drift: {header!r}"
        )

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    source_counts: dict[str, int] = defaultdict(int)

    seen_numbers: set[str] = set()

    for excel_row, raw in enumerate(values[2:], start=3):
        cells = [
            RowSupport.clean_cell(value)
            for value in raw
        ]

        if not RowSupport.has_meaningful_value(cells):
            continue

        while len(cells) < len(EXPECTED_HEADER):
            cells.append("")

        (
            source_no,
            municipality_name,
            facility_name,
            address,
            phone,
            ostomate_position,
            universal_sheet_position,
            available_time,
            source_note,
            jurisdiction,
            department,
            extra,
        ) = cells[:12]

        if extra:
            raise RuntimeError(
                f"row {excel_row}: unexpected extra value={extra!r}"
            )

        if not source_no:
            raise RuntimeError(
                f"row {excel_row}: blank NO."
            )

        if source_no in seen_numbers:
            raise RuntimeError(
                f"row {excel_row}: duplicate NO.={source_no!r}"
            )
        seen_numbers.add(source_no)

        if not municipality_name:
            raise RuntimeError(
                f"row {excel_row}: blank municipality"
            )

        code5 = MUNICIPALITY_BY_NAME.get(municipality_name)
        if not code5:
            raise RuntimeError(
                f"row {excel_row}: unknown municipality="
                f"{municipality_name!r}"
            )

        if not facility_name:
            raise RuntimeError(
                f"row {excel_row}: blank facility name"
            )

        if not address:
            raise RuntimeError(
                f"row {excel_row}: blank address"
            )

        source_counts[municipality_name] += 1

        # 中之条町は既存の自治体別ソースを優先。
        if code5 in EXCLUDED_CODES:
            continue

        row = {
            field: ""
            for field in schema
        }

        code6 = six_digit_municipality_code(code5)

        row["全国地方公共団体コード"] = code6
        row["所在地_全国地方公共団体コード"] = code6
        row["地方公共団体名"] = municipality_name

        row["名称"] = facility_name

        row["所在地_連結表記"] = address
        row["所在地_都道府県"] = "群馬県"
        row["所在地_市区町村"] = municipality_name

        if ostomate_position and ostomate_position != "－":
            row["オストメイト設置トイレ有無"] = "有"
        else:
            row["オストメイト設置トイレ有無"] = "無"

        row["利用可能時間特記事項"] = available_time

        row["ID"] = _ID_STRATEGY.generate(
            code5,
            source_no,
            facility_name,
            address,
        )

        RowSupport.append_labeled_note(
            row,
            "原データNO.",
            source_no,
        )
        RowSupport.append_labeled_note(
            row,
            "電話番号",
            phone,
        )
        RowSupport.append_labeled_note(
            row,
            "オストメイト対応多目的トイレ位置",
            ostomate_position,
        )
        RowSupport.append_labeled_note(
            row,
            "ユニバーサルシート設置多目的トイレ位置",
            universal_sheet_position,
        )
        RowSupport.append_labeled_note(
            row,
            "原データ備考",
            source_note,
        )
        RowSupport.append_labeled_note(
            row,
            "所管",
            jurisdiction,
        )
        RowSupport.append_labeled_note(
            row,
            "担当所属",
            department,
        )

        grouped[code5].append(row)

    actual_counts = dict(source_counts)

    if actual_counts != EXPECTED_COUNTS:
        raise RuntimeError(
            "municipality row counts changed: "
            f"actual={actual_counts!r} "
            f"expected={EXPECTED_COUNTS!r}"
        )

    if len(seen_numbers) != 339:
        raise RuntimeError(
            f"source row count={len(seen_numbers)} expected=339"
        )

    generated = 0
    total_rows = 0

    for code5, municipality_name in TARGETS:
        rows = grouped.get(code5, [])

        if not rows:
            raise RuntimeError(
                f"{code5}: no normalized rows"
            )

        ids = [
            row["ID"]
            for row in rows
        ]

        if len(ids) != len(set(ids)):
            raise RuntimeError(
                f"{code5}: duplicate generated ID"
            )

        dest = (
            OUT_ROOT
            / f"{code5}-{municipality_name}"
            / "public-toilet"
            / "public-toilet.csv"
        )

        if dest.exists():
            raise RuntimeError(
                f"{code5}: normalized already exists: {dest}"
            )

        _WRITER.write(
            dest,
            schema,
            rows,
        )

        generated += 1
        total_rows += len(rows)

        print(
            f"OK {code5} {municipality_name}: "
            f"rows={len(rows)}"
        )

    print(
        f"generated municipalities={generated} "
        f"rows={total_rows} "
        f"excluded={len(EXCLUDED_CODES)}"
    )


if __name__ == "__main__":
    main()
