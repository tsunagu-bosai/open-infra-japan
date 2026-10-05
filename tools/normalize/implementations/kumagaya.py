#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.normalization import RowSupport, StandardCsvWriter
from tools.normalize.core.schema import read_schema_fields

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

CODE = "11202"
NAME = "熊谷市"
PREF = "埼玉県"
PREF_DIR = "11-埼玉県"
MUN_DIR = "11202-熊谷市"
SOURCE_FILE = "11202_public-toilet.csv"

EXPECTED_HEADER = [
    "地方公共団体名",
    "地方公共団体名称",
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
    "建物名等_方書",
    "アドレスマッチング",
    "設置位置",
    "緯度",
    "経度",
    "高度の種別",
    "高度の値",
    "男性トイレ総数",
    "男性トイレ数_小便器",
    "男性トイレ数_和式",
    "男性トイレ数_洋式",
    "女性トイレ総数",
    "女性トイレ数_和式",
    "女性トイレ数_洋式",
    "男女共同トイレ総数",
    "男女共同トイレ数_和式",
    "男女共同トイレ数_洋式",
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
    "所管課",
    "経度",
    "緯度",
    "分類",
]

POSITIONAL_MAP = {
    2: "名称",
    3: "名称_カナ",
    4: "名称_英語",
    5: "所在地_全国地方公共団体コード",
    6: "町字ID",
    7: "所在地_連結表記",
    8: "所在地_都道府県",
    9: "所在地_市区町村",
    10: "所在地_町字",
    11: "所在地_番地以下",
    12: "建物名等(方書)",
    14: "設置位置",
    17: "高度の種別",
    18: "高度の値",
    19: "男性トイレ総数",
    20: "男性トイレ数（小便器）",
    21: "男性トイレ数（和式）",
    22: "男性トイレ数（洋式）",
    23: "女性トイレ総数",
    24: "女性トイレ数（和式）",
    25: "女性トイレ数（洋式）",
    26: "男女共用トイレ総数",
    27: "男女共用トイレ数（和式）",
    28: "男女共用トイレ数（洋式）",
    29: "バリアフリートイレ数",
    30: "車椅子使用者用トイレ有無",
    31: "乳幼児用設備設置トイレ有無",
    32: "オストメイト設置トイレ有無",
    33: "利用開始時間",
    34: "利用終了時間",
    35: "利用可能時間特記事項",
    36: "画像",
    37: "画像_ライセンス",
    38: "備考",
}



def read_rows(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise RuntimeError(f"{path}: empty CSV") from exc

        if header != EXPECTED_HEADER:
            raise RuntimeError(
                f"{path}: header mismatch\n"
                f"actual={header!r}\n"
                f"expected={EXPECTED_HEADER!r}"
            )

        rows: list[list[str]] = []
        for line_no, values in enumerate(reader, 2):
            if not RowSupport.has_meaningful_value(values):
                continue
            if len(values) != len(EXPECTED_HEADER):
                raise RuntimeError(
                    f"{path}:{line_no}: columns={len(values)} "
                    f"expected={len(EXPECTED_HEADER)}"
                )
            rows.append([RowSupport.clean(v) for v in values])

    if not rows:
        raise RuntimeError(f"{path}: no data rows")
    return rows


def prepare() -> tuple[Path, list[str], list[dict[str, str]]]:
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"{SCHEMA_PATH}: schema columns={len(schema)} expected=39")

    source = ROOT / "data/raw" / PREF_DIR / MUN_DIR / "public-toilet" / SOURCE_FILE
    dest = (
        ROOT / "data/normalized" / PREF_DIR / MUN_DIR
        / "public-toilet" / "public-toilet.csv"
    )

    rows = read_rows(source)
    code6 = six_digit_municipality_code(CODE)

    prepared: list[dict[str, str]] = []
    for line_no, values in enumerate(rows, 2):
        if values[0] != NAME:
            raise RuntimeError(f"{source}:{line_no}: 地方公共団体名={values[0]!r}")
        if values[1] != f"{PREF}{NAME}":
            raise RuntimeError(f"{source}:{line_no}: 地方公共団体名称={values[1]!r}")
        if values[5] != code6:
            raise RuntimeError(
                f"{source}:{line_no}: 所在地_全国地方公共団体コード="
                f"{values[5]!r} expected={code6!r}"
            )
        if values[15] or values[16]:
            raise RuntimeError(
                f"{source}:{line_no}: front coordinates unexpectedly populated "
                f"lat={values[15]!r} lon={values[16]!r}"
            )
        if not values[40] or not values[41]:
            raise RuntimeError(
                f"{source}:{line_no}: rear coordinates missing "
                f"lon={values[40]!r} lat={values[41]!r}"
            )
        if values[42] != "公衆トイレ一覧":
            raise RuntimeError(f"{source}:{line_no}: 分類={values[42]!r}")

        row = {field: "" for field in schema}
        row["全国地方公共団体コード"] = values[5]
        row["地方公共団体名"] = values[0]

        for src_index, target_name in POSITIONAL_MAP.items():
            row[target_name] = values[src_index]

        # 標準位置の緯度・経度は全件空欄。
        # 末尾の経度・緯度を標準列へ移す。
        row["経度"] = values[40]
        row["緯度"] = values[41]

        # 標準39列に存在しないソース項目は備考へ保持する。
        RowSupport.append_note(row, f"原データ地方公共団体名称={values[1]}")
        RowSupport.append_note(row, f"原データアドレスマッチング={values[13]}")
        RowSupport.append_note(row, f"原データ所管課={values[39]}")
        RowSupport.append_note(row, f"原データ分類={values[42]}")

        prepared.append(row)

    return dest, schema, prepared



def main() -> None:
    dest, schema, rows = prepare()
    print(f"preflight OK: {CODE} {NAME} rows={len(rows)}")
    StandardCsvWriter().write(dest, schema, rows)
    print(f"OK {CODE} {NAME}: rows={len(rows)} source={SOURCE_FILE}")


if __name__ == "__main__":
    main()
