#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from tools.normalize.core.normalization import RowSupport
from tools.normalize.core.schema import read_schema_fields

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"
SRC = ROOT / "data/raw/13-東京都/13109-品川区/public-toilet/13109_public-toilet.csv"
DEST = ROOT / "data/normalized/13-東京都/13109-品川区/public-toilet/public-toilet.csv"

EXPECTED = [
    '施設名', '施設名(英語)', '男性トイレ数', '女性トイレ数', '男女共用トイレ数',
    'バリアフリートイレ数', 'ベビーベッド(有、無)', 'オストメイト(有、無)',
    '利用可能時間OPENS', '利用可能時間CLOSES', '説明(日本語)', '説明(英語)',
    '緯度', '経度', '画像URL', '画像URL', '画像URL', '画像URL'
]



def main():
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")
    if not SRC.exists():
        raise RuntimeError(f"missing source: {SRC}")
    if DEST.exists():
        raise RuntimeError(f"normalized already exists: {DEST}")

    with SRC.open("r", encoding="cp932", newline="") as f:
        physical = list(csv.reader(f))

    header, data = physical[0], physical[1:]
    if header != EXPECTED:
        raise RuntimeError("source header drift")
    if not data:
        raise RuntimeError("source has no data rows")

    out = []
    for line_no, r in enumerate(data, 2):
        if len(r) != 18:
            raise RuntimeError(f"line {line_no}: width={len(r)}")

        c = [(v or "").strip() for v in r]

        # Extra semantic fields were confirmed blank in inspection.
        for idx, label in (
            (6, "ベビーベッド"),
            (7, "オストメイト"),
            (8, "利用可能時間OPENS"),
            (9, "利用可能時間CLOSES"),
            (11, "説明(英語)"),
            (14, "画像URL1"),
            (15, "画像URL2"),
            (16, "画像URL3"),
            (17, "画像URL4"),
        ):
            if c[idx]:
                raise RuntimeError(
                    f"line {line_no}: unexpected populated {label}={c[idx]!r}"
                )

        row = {k: "" for k in schema}
        row["全国地方公共団体コード"] = "131091"
        row["地方公共団体名"] = "品川区"
        row["名称"] = c[0]
        row["名称_英語"] = c[1]

        row["男性トイレ総数"] = c[2]
        row["女性トイレ総数"] = c[3]
        row["男女共用トイレ総数"] = c[4]
        row["バリアフリートイレ数"] = c[5]

        row["緯度"] = c[12]
        row["経度"] = c[13]

        if c[10]:
            RowSupport.append_note(row, f"原データ説明(日本語)={c[10]}")

        out.append(row)

    print("preflight OK: 品川区")
    print(
        f"rows={len(out)} code=131091 blank_ids={len(out)} "
        f"blank_addresses={len(out)}"
    )

    DEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = DEST.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=schema, lineterminator="\n")
        writer.writeheader()
        writer.writerows(out)
    tmp.replace(DEST)

    print(f"OK 13109 品川区: rows={len(out)} encoding=cp932")


if __name__ == "__main__":
    main()
