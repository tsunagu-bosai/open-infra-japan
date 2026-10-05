#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.xlsx import read_xlsx_values
from tools.normalize.core.normalization import RowSupport, StandardCsvWriter


ROOT = Path.cwd()

SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

SOURCE = (
    ROOT
    / "data/raw/33-岡山県/33681-吉備中央町/public-toilet/"
    "336815_public_toilet.xlsx"
)

DEST = (
    ROOT
    / "data/normalized/33-岡山県/33681-吉備中央町/public-toilet/"
    "public-toilet.csv"
)

CODE6 = "336815"
NAME = "吉備中央町"

BOOLEAN_FIELDS = (
    "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無",
)


def normalize_boolean(value: str, *, field: str, row_no: int) -> str:
    value = RowSupport.clean_cell(value)

    if value == "0":
        return "無"
    if value == "1":
        return "有"
    if value in {"", "有", "無"}:
        return value

    raise RuntimeError(
        f"row {row_no}: unexpected {field}={value!r}"
    )


def main() -> None:
    if not SOURCE.exists():
        raise RuntimeError(f"missing source: {SOURCE}")

    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    values = read_xlsx_values(SOURCE)

    if not values:
        raise RuntimeError("empty source")

    header = [RowSupport.clean_cell(v) for v in values[0]]

    if header != schema:
        raise RuntimeError(f"source header drift: {header!r}")

    source_rows = [row for row in values[1:] if RowSupport.has_meaningful_value(row)]
    if not source_rows:
        raise RuntimeError("no active source rows")

    rows: list[dict[str, str]] = []
    corrected_code_rows = 0
    converted_boolean_values = 0

    for row_no, values_row in enumerate(source_rows, start=2):
        if len(values_row) != len(schema):
            raise RuntimeError(
                f"row {row_no}: columns={len(values_row)} expected={len(schema)}"
            )

        row = {
            field: RowSupport.clean_cell(values_row[i])
            for i, field in enumerate(schema)
        }

        raw_code = row["全国地方公共団体コード"]

        if raw_code == CODE6:
            pass
        elif (
            raw_code == "336816"
            and row["名称"] == "加茂川庁舎前公住便所"
        ):
            row["全国地方公共団体コード"] = CODE6
            RowSupport.append_note(
                row,
                "原データ全国地方公共団体コード=336816",
            )
            corrected_code_rows += 1
        else:
            raise RuntimeError(
                f"row {row_no}: unexpected municipality code "
                f"{raw_code!r} name={row['名称']!r}"
            )

        if row["地方公共団体名"] != NAME:
            raise RuntimeError(
                f"row {row_no}: unexpected municipality name "
                f"{row['地方公共団体名']!r}"
            )

        if not row["名称"]:
            raise RuntimeError(f"row {row_no}: blank 名称")

        if not row["所在地_連結表記"]:
            raise RuntimeError(f"row {row_no}: blank 所在地_連結表記")

        for field in BOOLEAN_FIELDS:
            before = row[field]
            after = normalize_boolean(
                before,
                field=field,
                row_no=row_no,
            )
            if after != before:
                converted_boolean_values += 1
            row[field] = after

        rows.append(row)

    if corrected_code_rows != 1:
        raise RuntimeError(
            f"corrected municipality-code rows={corrected_code_rows} expected=1"
        )

    StandardCsvWriter().write(DEST, schema, rows)

    print(
        f"OK 33681 {NAME}: "
        f"rows={len(rows)} "
        f"code_corrected={corrected_code_rows} "
        f"boolean_values_converted={converted_boolean_values}"
    )


if __name__ == "__main__":
    main()
