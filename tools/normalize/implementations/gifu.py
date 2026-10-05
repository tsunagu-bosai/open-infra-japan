#!/usr/bin/env python3

import csv
import re
from pathlib import Path

from tools.normalize.core.normalization import (
    PreserveInvalidTimeStrategy,
    RowSupport,
    StandardCsvWriter,
)

ROOT = Path(__file__).resolve().parents[3]

SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

with SCHEMA_PATH.open("r", encoding="utf-8-sig", newline="") as f:
    STANDARD = [row["name"] for row in csv.DictReader(f)]

DIRECT = {
    "NO": "ID",
    "名称": "名称",
    "名称_カナ": "名称_カナ",
    "名称_英語": "名称_英語",
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
    "利用開始時間": "利用開始時間",
    "利用終了時間": "利用終了時間",
    "利用可能時間特記事項": "利用可能時間特記事項",
    "画像": "画像",
    "画像_ライセンス": "画像_ライセンス",
    "備考": "備考",
}


TIME_NORMALIZER = PreserveInvalidTimeStrategy()


SOURCE = (
    ROOT
    / "data/raw/21-岐阜県/21209-羽島市/public-toilet/"
      "212091_public_toilet_202403.csv"
)

OUTPUT = (
    ROOT
    / "data/normalized/21-岐阜県/21209-羽島市/public-toilet/"
      "public-toilet.csv"
)

CODE_FIELD = "都道府県コード\n又は市区町村コード"

EXPECTED_HEADER = [
    CODE_FIELD,
    "NO",
    "都道府県名",
    "市区町村名",
    "名称",
    "名称_カナ",
    "名称_英語",
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
    "画像",
    "画像_ライセンス",
    "備考",
]


def normalize_row(row):
    out = {key: "" for key in STANDARD}

    for source, target in DIRECT.items():
        out[target] = RowSupport.clean(row.get(source))

    code = RowSupport.clean(row.get(CODE_FIELD))
    if code == "212091":
        out["全国地方公共団体コード"] = code
    elif code:
        RowSupport.append_note(out, f"{CODE_FIELD}_原値:{code}")

    pref = RowSupport.clean(row.get("都道府県名"))
    city = RowSupport.clean(row.get("市区町村名"))

    if pref and city:
        out["地方公共団体名"] = pref + city
    elif city:
        out["地方公共団体名"] = city
    elif pref:
        out["地方公共団体名"] = pref

    out["所在地_都道府県"] = pref
    out["所在地_市区町村"] = city

    multi = RowSupport.clean(row.get("多機能トイレ数"))
    if multi:
        RowSupport.append_note(out, f"多機能トイレ数:{multi}")

    for field in (
        "車椅子使用者用トイレ有無",
        "乳幼児用設備設置トイレ有無",
        "オストメイト設置トイレ有無",
    ):
        value = RowSupport.clean(out[field])
        if value and value not in {"有", "無"}:
            RowSupport.append_note(out, f"{field}_原値:{value}")
            out[field] = ""

    for field in ("利用開始時間", "利用終了時間"):
        value, bad = TIME_NORMALIZER(out[field])
        out[field] = value
        if bad:
            RowSupport.append_note(out, f"{field}_原値:{bad}")

    return out


def main():
    with SOURCE.open(encoding="cp932", newline="") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames != EXPECTED_HEADER:
            raise SystemExit(f"unexpected header: {reader.fieldnames!r}")

        source_rows = list(reader)

    normalized = [
        normalize_row(row)
        for row in source_rows
        if any(RowSupport.clean(v) for v in row.values())
    ]

    StandardCsvWriter().write(OUTPUT, STANDARD, normalized)

    print(
        f"21209-羽島市 source={len(source_rows)} "
        f"normalized={len(normalized)} "
        f"type=legacy32-newline-header encoding=cp932"
    )


if __name__ == "__main__":
    main()
