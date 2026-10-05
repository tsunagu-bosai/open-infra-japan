#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.normalization import RowSupport, StandardCsvWriter


ROOT = Path.cwd()

SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

SRC = (
    ROOT
    / "data/raw/31-鳥取県/31201-鳥取市/public-toilet/public-facility.csv"
)

DEST = (
    ROOT
    / "data/normalized/31-鳥取県/31201-鳥取市/public-toilet/public-toilet.csv"
)

CODE5 = "31201"
NAME = "鳥取市"
EXPECTED_HEADER = [
    "itemID",
    "緯度",
    "経度",
    "建物名称",
    "所在地",
    "所属名称",
    "施設分類",
    "用途",
    "主要建物構造",
    "主な建築日",
    "延床面積（㎡）",
    "中学校区",
    "避難所指定等",
]





def main():
    if not SRC.exists():
        raise RuntimeError(f"missing source: {SRC}")

    schema = read_schema_fields(SCHEMA_PATH)

    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    with SRC.open("r", encoding="cp932", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        source_rows = list(reader)

    if header != EXPECTED_HEADER:
        raise RuntimeError(f"source header drift: {header!r}")

    if not source_rows:
        raise RuntimeError("source contains no data rows")

    code6 = six_digit_municipality_code(CODE5)

    target_rows = [
        row
        for row in source_rows
        if "便所" in RowSupport.clean(row.get("用途"))
    ]

    if not target_rows:
        raise RuntimeError("no rows matched 用途 containing 便所")

    rows = []
    ids = []

    for line_no, src in enumerate(target_rows, 2):
        c = {k: RowSupport.clean(v) for k, v in src.items()}

        for field in (
            "itemID",
            "建物名称",
            "所在地",
            "緯度",
            "経度",
        ):
            if not c[field]:
                raise RuntimeError(
                    f"line {line_no}: blank required source field {field}"
                )

        row = {field: "" for field in schema}

        row["全国地方公共団体コード"] = code6
        row["地方公共団体名"] = NAME
        row["ID"] = c["itemID"]
        row["名称"] = c["建物名称"]
        row["所在地_連結表記"] = c["所在地"]
        row["所在地_都道府県"] = "鳥取県"
        row["所在地_市区町村"] = NAME
        row["緯度"] = c["緯度"]
        row["経度"] = c["経度"]

        # 公共施設データ固有情報は意味を狭めず備考へ保存する。
        RowSupport.append_note(row, f"原データ用途={c['用途']}")
        RowSupport.append_note(row, f"原データ所属名称={c['所属名称']}")
        RowSupport.append_note(row, f"原データ施設分類={c['施設分類']}")

        ids.append(row["ID"])
        rows.append(row)

    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate ID")


    StandardCsvWriter().write(DEST, schema, rows)

    print(
        f"OK {CODE5} {NAME}: "
        f"source={len(source_rows)} "
        f"toilet={len(target_rows)} "
        f"normalized={len(rows)} "
        f"encoding=cp932"
    )


if __name__ == "__main__":
    main()
