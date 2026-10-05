#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.normalization import (
    RowSupport,
    StrictHmTimeStrategy,
    Sha256StableIdStrategy,
    StandardCsvWriter,
)
from tools.normalize.core.schema import read_schema_fields


ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

SOURCE = (
    ROOT
    / "data/raw/33-岡山県/prefecture/public-toilet/opendata_1442.csv"
)

DEST = (
    ROOT
    / "data/normalized/33-岡山県/33100-岡山市/public-toilet/public-toilet.csv"
)

CODE5 = "33100"
NAME = "岡山市"
EXPECTED_HEADER = [
    "名称",
    "住所",
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
    "経度",
    "緯度",
    "分類",
]

DIRECT_FIELDS = (
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
    "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無",
    "利用可能時間特記事項",
)


_ID_STRATEGY = Sha256StableIdStrategy(
    digest_length=12,
    template="{code}-{digest}",
)
_WRITER = StandardCsvWriter()
_TIME_STRATEGY = StrictHmTimeStrategy()




def main():
    if not SOURCE.exists():
        raise RuntimeError(f"missing source: {SOURCE}")

    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    with SOURCE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        source_rows = [
            source
            for source in reader
            if RowSupport.has_meaningful_value(source.values())
        ]

    if header != EXPECTED_HEADER:
        raise RuntimeError(f"source header drift: {header!r}")

    if not source_rows:
        raise RuntimeError("no source rows")

    code6 = six_digit_municipality_code(CODE5)

    rows = []
    ids = set()

    for line_no, source in enumerate(source_rows, start=2):
        src = {k: RowSupport.clean(v) for k, v in source.items()}

        if src["分類"] != "公衆トイレ":
            raise RuntimeError(
                f"line {line_no}: unexpected 分類={src['分類']!r}"
            )

        for field in ("名称", "住所", "緯度", "経度"):
            if not src[field]:
                raise RuntimeError(
                    f"line {line_no}: blank required field {field}"
                )

        for field in (
            "車椅子使用者用トイレ有無",
            "乳幼児用設備設置トイレ有無",
            "オストメイト設置トイレ有無",
        ):
            if src[field] not in {"有", "無"}:
                raise RuntimeError(
                    f"line {line_no}: invalid {field}={src[field]!r}"
                )

        row = {field: "" for field in schema}

        row["全国地方公共団体コード"] = code6
        row["所在地_全国地方公共団体コード"] = code6
        row["地方公共団体名"] = NAME

        row["名称"] = src["名称"]
        row["所在地_連結表記"] = src["住所"]
        row["所在地_都道府県"] = "岡山県"
        row["所在地_市区町村"] = NAME
        row["緯度"] = src["緯度"]
        row["経度"] = src["経度"]

        for field in DIRECT_FIELDS:
            row[field] = src[field]

        row["利用開始時間"] = _TIME_STRATEGY(src["利用開始時間"])
        row["利用終了時間"] = _TIME_STRATEGY(src["利用終了時間"])

        row["備考"] = src["備考"]

        if src["多機能トイレ数"]:
            RowSupport.append_note(
                row,
                f"原データ多機能トイレ数={src['多機能トイレ数']}",
            )

        ident = _ID_STRATEGY.generate(
            CODE5,
            src["名称"],
            src["住所"],
            src["緯度"],
            src["経度"],
        )

        if ident in ids:
            raise RuntimeError(
                f"line {line_no}: generated duplicate ID={ident}"
            )

        ids.add(ident)
        row["ID"] = ident

        RowSupport.append_note(
            row,
            "原データにID項目なし。自治体コード・名称・住所・緯度・経度から決定的IDを生成",
        )

        rows.append(row)

    _WRITER.write(DEST, schema, rows)

    print(
        f"OK {CODE5} {NAME}: "
        f"rows={len(rows)} "
        f"generated_ids={len(ids)} "
        f"encoding=utf-8-sig"
    )


if __name__ == "__main__":
    main()
