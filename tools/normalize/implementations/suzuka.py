#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from pathlib import Path

from tools.normalize.core.normalization import (
    RowSupport,
    StrictHmTimeStrategy,
    Sha256StableIdStrategy,
    StandardCsvWriter,
)
from tools.normalize.core.schema import read_schema_fields

ROOT = Path.cwd()
RAW = ROOT / "data/raw/24-三重県/24207-鈴鹿市/public-toilet/242071_public_toilet_20181001.csv"
OUT = ROOT / "data/normalized/24-三重県/24207-鈴鹿市/public-toilet/public-toilet.csv"
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {"24207-鈴鹿市"}
CODE6 = "242071"
MUNICIPALITY = "鈴鹿市"
PREFECTURE = "三重県"

EXPECTED_HEADER = [
    "都道府県コード又は市区町村コード",
    "都道府県名",
    "市区町村名",
    "名称",
    "名称_カナ",
    "住所",
    "方書",
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
    "多機能トイレ数",
    "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無",
    "利用開始時間",
    "利用終了時間",
    "利用可能時間特記事項",
    "備考",
]

DIRECT_MAP = {
    "名称": "名称",
    "名称_カナ": "名称_カナ",
    "住所": "所在地_連結表記",
    "方書": "建物名等(方書)",
    "設置位置": "設置位置",
    "緯度": "緯度",
    "経度": "経度",
    "男性トイレ総数": "男性トイレ総数",
    "男性トイレ数（小便器）": "男性トイレ数（小便器）",
    "男性トイレ数（和式）": "男性トイレ数（和式）",
    "男性トイレ数（洋式）": "男性トイレ数（洋式）",
    "女性トイレ総数": "女性トイレ総数",
    "女性トイレ数（和式）": "女性トイレ数（和式）",
    "女性トイレ数（洋式）": "女性トイレ数（洋式）",
    "男女共用トイレ総数": "男女共用トイレ総数",
    "男女共用トイレ数（和式）": "男女共用トイレ数（和式）",
    "男女共用トイレ数（洋式）": "男女共用トイレ数（洋式）",
    "車椅子使用者用トイレ有無": "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無": "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無": "オストメイト設置トイレ有無",
    "利用可能時間特記事項": "利用可能時間特記事項",
    "備考": "備考",
}


_ID_STRATEGY = Sha256StableIdStrategy(template="{code}-{digest}")
_WRITER = StandardCsvWriter()
_TIME_STRATEGY = StrictHmTimeStrategy()




def main():
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")
    if not RAW.exists():
        raise RuntimeError(f"missing raw: {RAW}")
    if OUT.exists():
        raise RuntimeError(f"normalized already exists: {OUT}")

    rows = []

    with RAW.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if (reader.fieldnames or []) != EXPECTED_HEADER:
            raise RuntimeError(
                f"unexpected header: actual={reader.fieldnames!r}"
            )

        for line_no, source in enumerate(reader, 2):
            source = {k: RowSupport.clean(v) for k, v in source.items()}
            if not any(source.values()):
                continue

            if source["都道府県コード又は市区町村コード"] != CODE6:
                raise RuntimeError(
                    f"line {line_no}: unexpected municipality code="
                    f"{source['都道府県コード又は市区町村コード']!r}"
                )
            if source["都道府県名"] != PREFECTURE:
                raise RuntimeError(
                    f"line {line_no}: unexpected prefecture={source['都道府県名']!r}"
                )
            if source["市区町村名"] != MUNICIPALITY:
                raise RuntimeError(
                    f"line {line_no}: unexpected municipality={source['市区町村名']!r}"
                )

            name = source["名称"]
            address = source["住所"]
            lat = source["緯度"]
            lon = source["経度"]

            if not name or not address or not lat or not lon:
                raise RuntimeError(
                    f"line {line_no}: required source field is blank"
                )

            row = {field: "" for field in schema}

            for source_field, output_field in DIRECT_MAP.items():
                row[output_field] = source[source_field]

            row["全国地方公共団体コード"] = CODE6
            row["ID"] = _ID_STRATEGY.generate("24207", name, address, lat, lon)
            row["地方公共団体名"] = MUNICIPALITY
            row["所在地_全国地方公共団体コード"] = CODE6
            row["所在地_都道府県"] = PREFECTURE
            row["所在地_市区町村"] = MUNICIPALITY
            row["利用開始時間"] = _TIME_STRATEGY(source["利用開始時間"])
            row["利用終了時間"] = _TIME_STRATEGY(source["利用終了時間"])

            multi = source["多機能トイレ数"]
            if multi:
                RowSupport.append_note(row, f"原データ多機能トイレ数={multi}")

            rows.append(row)

    if not rows:
        raise RuntimeError("no data rows")

    ids = [row["ID"] for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate IDs")

    _WRITER.write(OUT, schema, rows)

    print(f"24207-鈴鹿市 rows={len(rows)} source={RAW.name}")


if __name__ == "__main__":
    main()
