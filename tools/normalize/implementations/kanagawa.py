#!/usr/bin/env python3

import csv
from pathlib import Path
from tools.normalize.core.normalization import RowSupport

ROOT = Path(__file__).resolve().parents[3]

SOURCES = [
    (
        ROOT
        / "data/raw/14-神奈川県/14201-横須賀市/public-toilet/"
          "wagmap_lid_14.csv"
    ),
    (
        ROOT
        / "data/raw/14-神奈川県/14201-横須賀市/public-toilet/"
          "wagmap_lid_15.csv"
    ),
]

OUTPUT = (
    ROOT
    / "data/normalized/14-神奈川県/14201-横須賀市/public-toilet/"
      "public-toilet.csv"
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
    "名称",
    "名称カナ",
    "住所",
    "TEL",
    "FAX",
    "URL",
    "備考",
    "備考２",
    "備考３",
    "備考４",
    "備考５",
    "経度",
    "緯度",
    "分類",
]



def add_note(out, key, value):
    value = RowSupport.clean(value)
    if not value:
        return

    part = f"{key}:{value}"
    old = RowSupport.clean(out["備考"])
    out["備考"] = f"{old} / {part}" if old else part


def normalize_row(row):
    out = {key: "" for key in STANDARD}

    out["名称"] = RowSupport.clean(row["名称"])
    out["名称_カナ"] = RowSupport.clean(row["名称カナ"])
    out["所在地_連結表記"] = RowSupport.clean(row["住所"])
    out["緯度"] = RowSupport.clean(row["緯度"])
    out["経度"] = RowSupport.clean(row["経度"])

    # 原典の備考はそのまま保持。
    out["備考"] = RowSupport.clean(row["備考"])

    # 「備考２」に明示されたおむつ替え設備だけ標準列へ反映する。
    # 「だれでもトイレ」は存在を示すが、標準列は件数のため
    # 件数を推測して「バリアフリートイレ数」へは変換しない。
    if "おむつ替えシートあり" in RowSupport.clean(row["備考２"]):
        out["乳幼児用設備設置トイレ有無"] = "有"

    # 標準39列に直接対応しない値は備考へ原文保存。
    for key in (
        "TEL",
        "FAX",
        "URL",
        "備考２",
        "備考３",
        "備考４",
        "備考５",
        "分類",
    ):
        add_note(out, key, row[key])

    return out


def main():
    all_rows = []

    for source in SOURCES:
        with source.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            if reader.fieldnames != EXPECTED_HEADER:
                raise SystemExit(
                    f"unexpected header: {source}\n"
                    f"{reader.fieldnames!r}"
                )

            rows = [
                row
                for row in reader
                if any(RowSupport.clean(v) for v in row.values())
            ]

        print(f"{source.name}: source={len(rows)}")
        all_rows.extend(rows)

    normalized = [normalize_row(row) for row in all_rows]

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
        f"14201-横須賀市 source={len(all_rows)} "
        f"normalized={len(normalized)} "
        f"type=wagmap14 encoding=utf-8-sig"
    )


if __name__ == "__main__":
    main()
