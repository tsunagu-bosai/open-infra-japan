#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.normalization import (
    RowSupport,
    Sha256StableIdStrategy,
    StandardCsvWriter,
)
from tools.normalize.core.schema import read_schema_fields


ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"
RAW = (
    ROOT
    / "data/raw/29-奈良県/29000-奈良県/public-toilet/"
    / "210408toirezyouhou.csv"
)
DEST = (
    ROOT
    / "data/normalized/29-奈良県/29201-奈良市/"
    / "public-toilet/public-toilet.csv"
)

TARGETS = {"29201": "奈良市"}

EXPECTED_HEADER = (
    "番号",
    "名称",
    "名称＿カナ",
    "住所",
    "設置位置",
    "男性トイレ便器総数",
    "男性トイレ小便器数",
    "男性トイレ和式大便器数",
    "男性トイレ洋式大便器数",
    "女性トイレ便器総数",
    "女性トイレ和式便器数",
    "女性トイレ洋式便器数",
    "多機能トイレ数",
    "車椅子使用者利用可能トイレ有無",
    "乳幼児用設備設置有無",
    "オストメイト設置有無",
    "管理者",
    "備考",
)

EXPECTED_ROWS = 25

FIELD_MAP = {
    "名称": "名称",
    "名称＿カナ": "名称_カナ",
    "住所": "所在地_連結表記",
    "設置位置": "設置位置",
    "男性トイレ便器総数": "男性トイレ総数",
    "男性トイレ小便器数": "男性トイレ数（小便器）",
    "男性トイレ和式大便器数": "男性トイレ数（和式）",
    "男性トイレ洋式大便器数": "男性トイレ数（洋式）",
    "女性トイレ便器総数": "女性トイレ総数",
    "女性トイレ和式便器数": "女性トイレ数（和式）",
    "女性トイレ洋式便器数": "女性トイレ数（洋式）",
    "車椅子使用者利用可能トイレ有無": "車椅子使用者用トイレ有無",
    "乳幼児用設備設置有無": "乳幼児用設備設置トイレ有無",
    "オストメイト設置有無": "オストメイト設置トイレ有無",
}

ID_STRATEGY = Sha256StableIdStrategy()


def clean(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def read_source() -> list[dict[str, str]]:
    if not RAW.exists():
        raise RuntimeError(f"missing source: {RAW}")

    with RAW.open(encoding="cp932", newline="") as f:
        reader = csv.DictReader(f)
        header = tuple(reader.fieldnames or [])

        if header != EXPECTED_HEADER:
            raise RuntimeError(
                f"{RAW.name}: header drift: columns={len(header)} "
                f"expected={len(EXPECTED_HEADER)}"
            )

        rows = [
            {
                key: clean(value)
                for key, value in row.items()
            }
            for row in reader
            if any(clean(value) for value in row.values())
        ]

    if len(rows) != EXPECTED_ROWS:
        raise RuntimeError(
            f"{RAW.name}: rows={len(rows)} expected={EXPECTED_ROWS}"
        )

    return rows


def main() -> None:
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    municipality_code = "29201"
    standard_code = six_digit_municipality_code(municipality_code)

    out: list[dict[str, str]] = []

    for line_no, src in enumerate(read_source(), start=2):
        source_no = src["番号"]
        name = src["名称"]
        address = src["住所"]

        if not source_no or not name or not address:
            raise RuntimeError(
                f"{RAW.name}:{line_no}: required field missing"
            )

        row = {field: "" for field in schema}

        row["全国地方公共団体コード"] = standard_code
        row["所在地_全国地方公共団体コード"] = standard_code
        row["地方公共団体名"] = "奈良市"
        row["所在地_都道府県"] = "奈良県"
        row["所在地_市区町村"] = "奈良市"

        for source_field, standard_field in FIELD_MAP.items():
            row[standard_field] = src[source_field]

        row["ID"] = ID_STRATEGY.generate(
            municipality_code,
            "nara-park",
            source_no,
            name,
            address,
        )

        RowSupport.append_note(row, f"原データ番号={source_no}")

        multi = src["多機能トイレ数"]
        if multi:
            RowSupport.append_note(
                row,
                f"原データ多機能トイレ数={multi}",
            )

        manager = src["管理者"]
        if manager:
            RowSupport.append_note(
                row,
                f"管理者={manager.strip()}",
            )

        source_note = src["備考"]
        if source_note:
            RowSupport.append_note(
                row,
                f"原データ備考={source_note}",
            )

        RowSupport.append_note(
            row,
            "出典=奈良県「奈良公園周辺トイレ一覧」",
        )

        out.append(row)

    ids = [row["ID"] for row in out]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate normalized IDs")

    if DEST.exists():
        raise RuntimeError(f"normalized already exists: {DEST}")

    StandardCsvWriter().write(DEST, schema, out)


if __name__ == "__main__":
    main()
