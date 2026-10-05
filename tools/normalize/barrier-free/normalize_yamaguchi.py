#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

import xlrd

from schema import FIELDS


ROOT = Path(__file__).resolve().parents[3]

SOURCE = (
    ROOT
    / "data/raw/35-山口県/barrier-free/"
    "yamaguchi-barrier-free/207634.xls"
)

OUTPUT = (
    ROOT
    / "data/normalized/35-山口県/barrier-free/"
    "yamaguchi-barrier-free.csv"
)

SOURCE_NAME = "山口県バリアフリー施設データベース"
SOURCE_URL = (
    "https://www.pref.yamaguchi.lg.jp/"
    "uploaded/attachment/207634.xls"
)

EXPECTED_SOURCE_ROWS = 1219
EXPECTED_OUTPUT_ROWS = 1151

MUNICIPALITIES = {
    "下関市": "35201",
    "宇部市": "35202",
    "山口市": "35203",
    "萩市": "35204",
    "防府市": "35206",
    "下松市": "35207",
    "岩国市": "35208",
    "光市": "35210",
    "長門市": "35211",
    "柳井市": "35212",
    "美祢市": "35213",
    "周南市": "35215",
    "山陽小野田市": "35216",
    "周防大島町": "35305",
    "和木町": "35321",
    "上関町": "35341",
    "田布施町": "35343",
    "平生町": "35344",
    "阿武町": "35502",
}

TOILET_FIELDS = (
    "障害者トイレ",
    "多目的トイレ（乳児シート）",
    "多目的トイレ（オストメイト）",
    "洋式トイレ",
    "男子用トイレ手すり",
    "授乳室",
)


def clean(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def main() -> None:
    if len(FIELDS) != 48:
        raise RuntimeError(
            f"schema columns={len(FIELDS)} expected=48"
        )

    book = xlrd.open_workbook(SOURCE)
    sheet = book.sheet_by_name("データベース")

    header_row = 49
    start_col = 10

    headers = [
        clean(sheet.cell_value(header_row, c)).replace("\n", "")
        for c in range(start_col, sheet.ncols)
    ]

    expected_headers = {
        "施設名",
        "地域",
        "施設区分",
        "付近住所",
        "障害者トイレ",
        "多目的トイレ（乳児シート）",
        "多目的トイレ（オストメイト）",
        "洋式トイレ",
        "男子用トイレ手すり",
        "授乳室",
    }

    missing = expected_headers - set(headers)
    if missing:
        raise RuntimeError(
            f"missing headers: {sorted(missing)}"
        )

    source_rows = []

    for r in range(header_row + 1, sheet.nrows):
        values = [
            clean(sheet.cell_value(r, c))
            for c in range(start_col, sheet.ncols)
        ]

        src = dict(zip(headers, values))

        if not src.get("施設名"):
            continue

        source_rows.append((r + 1, src))

    if len(source_rows) != EXPECTED_SOURCE_ROWS:
        raise RuntimeError(
            f"source rows={len(source_rows)} "
            f"expected={EXPECTED_SOURCE_ROWS}"
        )

    rows = []

    for excel_row, src in source_rows:
        if not any(
            src.get(field) == "○"
            for field in TOILET_FIELDS
        ):
            continue

        municipality = src["地域"]
        code = MUNICIPALITIES.get(municipality)

        if not code:
            raise RuntimeError(
                f"unknown municipality: "
                f"row={excel_row} value={municipality!r}"
            )

        row = {field: "" for field in FIELDS}

        row["prefecture_code"] = "35"
        row["prefecture_name"] = "山口県"
        row["municipality_code"] = code
        row["municipality_name"] = municipality

        row["facility_name"] = src["施設名"]
        row["facility_category"] = src["施設区分"]
        row["address"] = src["付近住所"]

        if src["障害者トイレ"] == "○":
            row["wheelchair_toilet"] = "yes"

        if (
            src["多目的トイレ（乳児シート）"] == "○"
            or src["多目的トイレ（オストメイト）"] == "○"
        ):
            row["multipurpose_toilet"] = "yes"

        if src["多目的トイレ（乳児シート）"] == "○":
            row["baby_bed"] = "yes"

        if src["多目的トイレ（オストメイト）"] == "○":
            row["ostomate"] = "yes"

        if src["授乳室"] == "○":
            row["nursing_space"] = "yes"

        notes = []

        if src["洋式トイレ"] == "○":
            notes.append("洋式トイレあり")

        if src["男子用トイレ手すり"] == "○":
            notes.append("男子用トイレ手すりあり")

        row["attribute_note"] = " / ".join(notes)

        row["source_dataset"] = "yamaguchi-barrier-free"
        row["source_name"] = SOURCE_NAME
        row["source_url"] = SOURCE_URL
        row["source_row"] = str(excel_row)

        rows.append(row)

    if len(rows) != EXPECTED_OUTPUT_ROWS:
        raise RuntimeError(
            f"output rows={len(rows)} "
            f"expected={EXPECTED_OUTPUT_ROWS}"
        )

    source_ids = [r["source_row"] for r in rows]
    if len(source_ids) != len(set(source_ids)):
        raise RuntimeError("duplicate source_row")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"OK rows={len(rows)}")
    print(f"output={OUTPUT}")


if __name__ == "__main__":
    main()
