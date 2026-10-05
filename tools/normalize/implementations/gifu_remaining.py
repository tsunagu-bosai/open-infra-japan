#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import xlrd
from tools import normalize_public_toilet as common
from tools.normalize.core.normalization import (
    RowSupport,
    Sha256StableIdStrategy,
    StandardCsvWriter,
)
from tools.normalize.core.schema import read_schema_fields

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "schema/standard/public-toilet/schema.csv"
SOURCE = ROOT / "data/raw/21-岐阜県/21208-瑞浪市/public-toilet/21208_public-toilet.xls"
OUTPUT = ROOT / "data/normalized/21-岐阜県/21208-瑞浪市/public-toilet/public-toilet.csv"

TARGETS = {"21208": "瑞浪市"}
EXPECTED_HEADER = ["施設名称", "所在地", "所管"]


def clean_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return str(int(value))
    return str(value).strip()


_ID_STRATEGY = Sha256StableIdStrategy(
    digest_length=12,
    template="{code}-SRC-{digest}",
)
_WRITER = StandardCsvWriter()


def main() -> None:
    if "21208" not in TARGETS:
        return
    if OUTPUT.exists():
        raise RuntimeError(f"21208: normalized already exists: {OUTPUT}")

    schema = read_schema_fields(SCHEMA)
    book = xlrd.open_workbook(SOURCE)
    sheet = book.sheet_by_name("Sheet1")

    header = [clean_cell(sheet.cell_value(2, c)) for c in range(sheet.ncols)]
    if header != EXPECTED_HEADER:
        raise RuntimeError(f"21208: unexpected header: {header!r}")

    source_rows = []
    for r in range(3, sheet.nrows):
        values = [clean_cell(sheet.cell_value(r, c)) for c in range(sheet.ncols)]
        if any(values):
            source_rows.append(values)

    if not source_rows:
        raise RuntimeError("21208: no data rows")

    normalized = []
    seen_ids: set[str] = set()

    for values in source_rows:
        src = dict(zip(EXPECTED_HEADER, values))
        name = clean_cell(src["施設名称"])
        address = clean_cell(src["所在地"])
        department = clean_cell(src["所管"])

        if not name or not address:
            raise RuntimeError(f"21208: missing name/address: {values!r}")

        ident = _ID_STRATEGY.generate("21208", name, address)
        if ident in seen_ids:
            raise RuntimeError(f"21208: generated duplicate ID: {ident}")
        seen_ids.add(ident)

        row = {field: "" for field in schema}
        row["全国地方公共団体コード"] = "212083"
        row["ID"] = ident
        row["地方公共団体名"] = "岐阜県瑞浪市"
        row["名称"] = name
        row["所在地_全国地方公共団体コード"] = "212083"
        row["所在地_連結表記"] = (
            address if address.startswith("岐阜県") else f"岐阜県{address}"
        )
        row["所在地_都道府県"] = "岐阜県"
        row["所在地_市区町村"] = "瑞浪市"

        RowSupport.append_note(
            row,
            "原データにID項目なし。施設名称・所在地から決定的IDを生成"
        )
        if department:
            RowSupport.append_note(row, f"所管={department}")

        normalized.append(row)

    patches = common.load_patches("21-岐阜県", "21208-瑞浪市")
    applied, problems = common.apply_patches(normalized, patches, SOURCE)
    if problems:
        raise RuntimeError(
            "21208-瑞浪市: patch適用失敗: " + " | ".join(map(str, problems))
        )

    _WRITER.write(OUTPUT, schema, normalized)

    print(
        f"OK 21208 瑞浪市: rows={len(normalized)} "
        f"generated_ids={len(normalized)} patches={applied}"
    )


if __name__ == "__main__":
    main()
