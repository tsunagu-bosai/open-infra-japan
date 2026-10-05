#!/usr/bin/env python3

import csv
import re
from pathlib import Path
from tools.normalize.core.normalization import (
    PreserveInvalidTimeStrategy,
    RowSupport,
)

ROOT = Path.cwd()

SOURCE = (
    ROOT
    / "data/raw/06-山形県/06363-舟形町/public-toilet/063631_public_toilet.csv"
)
OUTPUT = (
    ROOT
    / "data/normalized/06-山形県/06363-舟形町/public-toilet/public-toilet.csv"
)

STANDARD = [
    "全国地方公共団体コード",
    "ID",
    "地方公共団体名",
    "名称",
    "名称_カナ",
    "名称_英語",
    "所在地_全国地方公共団体コード",
    "町字ID",
    "所在地_連結表記",
    "所在地_都道府県",
    "所在地_市区町村",
    "所在地_町字",
    "所在地_番地以下",
    "建物名等(方書)",
    "設置位置",
    "緯度",
    "経度",
    "高度の種別",
    "高度の値",
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
    "バリアフリートイレ数",
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

EXPECTED_HEADER = [
    "都道府県コード又は市区町村コード",
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



def add_note(out, key, value):
    value = RowSupport.clean(value)
    if not value:
        return

    part = f"{key}:{value}"
    old = RowSupport.clean(out["備考"])
    out["備考"] = f"{old} / {part}" if old else part


TIME_NORMALIZER = PreserveInvalidTimeStrategy()


def normalize_row(row):
    out = {key: "" for key in STANDARD}

    for source, target in DIRECT.items():
        out[target] = RowSupport.clean(row.get(source))

    code = RowSupport.clean(row.get("都道府県コード又は市区町村コード"))
    if code == "063631":
        out["全国地方公共団体コード"] = code
    elif code:
        add_note(out, "都道府県コード又は市区町村コード_原値", code)

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
        add_note(out, "多機能トイレ数", multi)

    for field in (
        "車椅子使用者用トイレ有無",
        "乳幼児用設備設置トイレ有無",
        "オストメイト設置トイレ有無",
    ):
        value = RowSupport.clean(out[field])
        if value and value not in {"有", "無"}:
            add_note(out, f"{field}_原値", value)
            out[field] = ""

    for field in ("利用開始時間", "利用終了時間"):
        value, bad = TIME_NORMALIZER(out[field])
        out[field] = value
        if bad:
            add_note(out, f"{field}_原値", bad)

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

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=STANDARD,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(normalized)

    print(
        f"06363-舟形町 source={len(source_rows)} "
        f"normalized={len(normalized)} "
        f"type=legacy32 encoding=cp932"
    )


if __name__ == "__main__":
    main()
