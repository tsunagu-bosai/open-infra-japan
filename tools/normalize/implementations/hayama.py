#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import xlrd

from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.normalization import (
    RowSupport,
    Sha256StableIdStrategy,
    StandardCsvWriter,
)
from tools.normalize.core.municipality import six_digit_municipality_code

ROOT = Path.cwd()

SOURCE = (
    ROOT
    / "data/raw/14-神奈川県/14301-葉山町/public-toilet/public_toilet.xls"
)
DEST = (
    ROOT
    / "data/normalized/14-神奈川県/14301-葉山町/public-toilet/public-toilet.csv"
)
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"


STABLE_ID = Sha256StableIdStrategy()
WRITER = StandardCsvWriter()


def main() -> None:
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    if not SOURCE.exists():
        raise RuntimeError(f"14301: raw missing: {SOURCE}")

    if DEST.exists():
        raise RuntimeError(f"14301: normalized already exists: {DEST}")

    book = xlrd.open_workbook(SOURCE)

    expected_sheet = "トイレ一覧（令和７年12月23日更新）"
    if expected_sheet not in book.sheet_names():
        raise RuntimeError(
            f"14301: expected sheet missing: {expected_sheet!r}"
        )

    sheet = book.sheet_by_name(expected_sheet)

    if sheet.nrows < 3 or sheet.ncols < 6:
        raise RuntimeError(
            f"14301: unexpected sheet shape={sheet.nrows}x{sheet.ncols}"
        )

    headers = [RowSupport.clean(sheet.cell_value(1, c)) for c in range(6)]
    expected_headers = [
        "トイレ名称",
        "所　　　在",
        "男性用",
        "女性用",
        "多目的",
        "",
    ]

    if headers != expected_headers:
        raise RuntimeError(
            f"14301: unexpected headers={headers!r}"
        )

    code6 = six_digit_municipality_code("14301")
    rows = []
    deleted = 0

    for r in range(2, sheet.nrows):
        name = RowSupport.clean(sheet.cell_value(r, 0))
        address = RowSupport.clean(sheet.cell_value(r, 1))
        male = RowSupport.clean(sheet.cell_value(r, 2))
        female = RowSupport.clean(sheet.cell_value(r, 3))
        multipurpose = RowSupport.clean(sheet.cell_value(r, 4))
        status = RowSupport.clean(sheet.cell_value(r, 5))

        if status:
            if name == "仙元山公衆トイレ" and status == "削除":
                deleted += 1
                continue

            raise RuntimeError(
                f"14301 row {r + 1}: unexpected status={status!r}"
            )

        if not name or not address:
            raise RuntimeError(
                f"14301 row {r + 1}: missing name/address"
            )

        for label, value in (
            ("男性用", male),
            ("女性用", female),
            ("多目的", multipurpose),
        ):
            if value not in {"", "〇"}:
                raise RuntimeError(
                    f"14301 row {r + 1}: "
                    f"unexpected {label}={value!r}"
                )

        row = {c: "" for c in schema}

        row["全国地方公共団体コード"] = code6
        row["ID"] = STABLE_ID.generate("14301", name, address)
        row["地方公共団体名"] = "葉山町"

        row["名称"] = name

        row["所在地_全国地方公共団体コード"] = code6
        row["所在地_連結表記"] = f"神奈川県三浦郡{address}"
        row["所在地_都道府県"] = "神奈川県"
        row["所在地_市区町村"] = "葉山町"

        if male:
            RowSupport.append_note(row, "原データ男性用=〇")
        if female:
            RowSupport.append_note(row, "原データ女性用=〇")
        if multipurpose:
            RowSupport.append_note(row, "原データ多目的=〇")

        rows.append(row)

    if not rows:
        raise RuntimeError("14301: no active data rows")

    WRITER.write(DEST, schema, rows)

    print(
        f"OK 14301 葉山町: rows={len(rows)} "
        f"deleted={deleted}"
    )


if __name__ == "__main__":
    main()
