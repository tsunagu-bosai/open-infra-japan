#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from tools.normalize.core.normalization import RowSupport
from tools.normalize.core.schema import read_schema_fields

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"
SRC = ROOT / "data/raw/28-兵庫県/28208-相生市/public-toilet/28208_public-toilet.csv"
DEST = ROOT / "data/normalized/28-兵庫県/28208-相生市/public-toilet/public-toilet.csv"

EXPECTED_HEADER = [
    'OBJECTID', '市区町村コード', '番号', '都道府県名', '市区町村名',
    '名称', '名称_カナ', '所在_市', '所在_大字町丁目', '所在_住所/番地',
    '所在_方書', '設置位置', '緯度', '経度',
    '男性トイレ総数', '男性トイレ数（小便器）', '男性トイレ数（和式）',
    '男性トイレ数（洋式）', '女性トイレ総数', '女性トイレ数（和式）',
    '女性トイレ数（洋式）', '男女共用トイレ総数',
    '男女共用トイレ数（和式）', '男女共用トイレ数（洋式）',
    '多機能トイレ数', '車椅子使用者用トイレ有無',
    '乳幼児用設備設置トイレ有無', 'オストメイト設置トイレ有無',
    '利用可能時間\n特記事項', 'x', 'y'
]



def build_address(city, choaza, banchi, katagaki):
    city = (city or "").strip()
    choaza = (choaza or "").strip()
    banchi = (banchi or "").strip()
    katagaki = (katagaki or "").strip()

    # One source row already embeds "相生市" in 所在_大字町丁目.
    if choaza.startswith(city):
        base = choaza
    else:
        base = f"{city}{choaza}"

    if banchi:
        base += banchi
    if katagaki:
        base += katagaki
    return base


def main():
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")
    if not SRC.exists():
        raise RuntimeError(f"missing source: {SRC}")
    if DEST.exists():
        raise RuntimeError(f"normalized already exists: {DEST}")

    with SRC.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        srcrows = list(reader)

    if header != EXPECTED_HEADER:
        raise RuntimeError("source header drift")
    if not srcrows:
        raise RuntimeError("source has no data rows")

    out = []
    ids = []
    for line_no, s in enumerate(srcrows, 2):
        c = {k: (v or "").strip() for k, v in s.items()}

        if c["市区町村コード"] != "282081":
            raise RuntimeError(f"line {line_no}: unexpected municipality code")
        if c["番号"]:
            raise RuntimeError(f"line {line_no}: 番号 unexpectedly populated")

        objid = c["OBJECTID"]
        if not objid:
            raise RuntimeError(f"line {line_no}: blank OBJECTID")
        ids.append(objid)

        # Confirm x/y duplicate the canonical coordinate fields.
        if c["x"] != c["経度"] or c["y"] != c["緯度"]:
            raise RuntimeError(
                f"line {line_no}: x/y mismatch "
                f"x={c['x']!r} lon={c['経度']!r} "
                f"y={c['y']!r} lat={c['緯度']!r}"
            )

        row = {k: "" for k in schema}
        row["全国地方公共団体コード"] = c["市区町村コード"]
        row["地方公共団体名"] = c["市区町村名"]
        row["ID"] = objid
        row["名称"] = c["名称"]
        row["名称_カナ"] = c["名称_カナ"]

        row["所在地_都道府県"] = c["都道府県名"]
        row["所在地_市区町村"] = c["所在_市"]
        row["所在地_町字"] = c["所在_大字町丁目"]
        row["所在地_番地以下"] = c["所在_住所/番地"]
        row["建物名等(方書)"] = c["所在_方書"]
        row["所在地_連結表記"] = build_address(
            c["所在_市"],
            c["所在_大字町丁目"],
            c["所在_住所/番地"],
            c["所在_方書"],
        )

        row["設置位置"] = c["設置位置"]
        row["緯度"] = c["緯度"]
        row["経度"] = c["経度"]

        for field in (
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
        ):
            row[field] = c[field]

        row["利用可能時間特記事項"] = c["利用可能時間\n特記事項"]

        # Do not equate 多機能トイレ数 with バリアフリートイレ数.
        if c["多機能トイレ数"]:
            RowSupport.append_note(row, f"原データ多機能トイレ数={c['多機能トイレ数']}")

        out.append(row)

    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate OBJECTID")

    print("preflight OK: 相生市")
    print(
        f"rows={len(out)} code=282081 objectid_as_id={len(out)} "
        f"xy_verified={len(out)}"
    )

    DEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = DEST.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=schema, lineterminator="\n")
        writer.writeheader()
        writer.writerows(out)
    tmp.replace(DEST)

    print(f"OK 28208 相生市: rows={len(out)} encoding=utf-8-sig")


if __name__ == "__main__":
    main()
