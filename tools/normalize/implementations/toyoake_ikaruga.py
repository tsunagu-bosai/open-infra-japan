#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

from tools.normalize.core.normalization import RowSupport, StandardCsvWriter

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"



def read_schema() -> list[str]:
    with SCHEMA_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        fields = [row["name"] for row in csv.DictReader(f)]

    if len(fields) != 39:
        raise RuntimeError(f"expected 39 schema columns, got {len(fields)}")

    if "バリアフリートイレ数" not in fields:
        raise RuntimeError("canonical schema missing バリアフリートイレ数")

    if "多機能トイレ数" in fields:
        raise RuntimeError("legacy 多機能トイレ数 unexpectedly exists in canonical schema")

    return fields


def blank_row(schema: list[str]) -> dict[str, str]:
    return {field: "" for field in schema}




def normalize_toyoake(schema: list[str]) -> None:
    src = (
        ROOT
        / "data/raw/23-愛知県/23229-豊明市/public-toilet/public-toilet.csv"
    )
    dst = (
        ROOT
        / "data/normalized/23-愛知県/23229-豊明市/public-toilet/public-toilet.csv"
    )

    with src.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    out_rows: list[dict[str, str]] = []

    for line_no, row in enumerate(rows, 2):
        if RowSupport.clean(row.get("全国地方公共団体コード")) != "23229":
            raise RuntimeError(
                f"豊明市 line {line_no}: unexpected municipality code="
                f"{row.get('全国地方公共団体コード')!r}"
            )

        out = blank_row(schema)

        out.update({
            "全国地方公共団体コード": "232297",

            # 原データに安定したID項目がないため、IDは捏造しない。
            "ID": "",

            "地方公共団体名": "豊明市",
            "名称": RowSupport.clean(row.get("名称")),

            "所在地_全国地方公共団体コード": "232297",
            "所在地_連結表記": RowSupport.clean(row.get("住所表記")),
            "所在地_都道府県": "愛知県",
            "所在地_市区町村": "豊明市",

            "緯度": RowSupport.clean(row.get("緯度")),
            "経度": RowSupport.clean(row.get("経度")),

            "男性トイレ総数": RowSupport.clean(row.get("男性トイレ数（総数）")),
            "男性トイレ数（小便器）": RowSupport.clean(row.get("男性トイレ数（小便器）")),
            "男性トイレ数（和式）": RowSupport.clean(row.get("男声トイレ数(和式）")),
            "男性トイレ数（洋式）": RowSupport.clean(row.get("男性トイレ数（洋式）")),

            "女性トイレ総数": RowSupport.clean(row.get("女性トイレ数（総数）")),
            "女性トイレ数（和式）": RowSupport.clean(row.get("女性トイレ数(和式）")),
            "女性トイレ数（洋式）": RowSupport.clean(row.get("女性トイレ数（洋式）")),

            "車椅子使用者用トイレ有無":
                RowSupport.clean(row.get("車椅子使用者用トイレ有無")),
            "乳幼児用設備設置トイレ有無":
                RowSupport.clean(row.get("乳幼児設備設置トイレ有無")),
            "オストメイト設置トイレ有無":
                RowSupport.clean(row.get("オストメイト設置トイレ有無")),

            # 原データの「終日」等は時刻値へ推測変換せず特記事項へ保持。
            "利用可能時間特記事項": RowSupport.clean(row.get("利用時間")),

            "備考": RowSupport.clean(row.get("備考")),
        })

        multipurpose = RowSupport.clean(row.get("多機能トイレ数"))
        if multipurpose:
            # 多機能トイレ数はバリアフリートイレ数と同義とは限らない。
            RowSupport.append_note(out, f"原データ多機能トイレ数={multipurpose}")

        if not out["名称"]:
            raise RuntimeError(f"豊明市 line {line_no}: blank 名称")

        out_rows.append(out)

    if not out_rows:
        raise RuntimeError("豊明市: source produced no data rows")

    StandardCsvWriter().write(dst, schema, out_rows)
    print(f"豊明市: {len(out_rows)}")


def normalize_ikaruga(schema: list[str]) -> None:
    src = (
        ROOT
        / "data/raw/29-奈良県/29344-斑鳩町/public-toilet/public-toilet.csv"
    )
    dst = (
        ROOT
        / "data/normalized/29-奈良県/29344-斑鳩町/public-toilet/public-toilet.csv"
    )

    with src.open(encoding="cp932", newline="") as f:
        rows = list(csv.DictReader(f))

    out_rows: list[dict[str, str]] = []

    for line_no, row in enumerate(rows, 2):
        code6 = RowSupport.clean(row.get("都道府県コード又は市区町村コード"))

        if code6 != "293440":
            raise RuntimeError(
                f"斑鳩町 line {line_no}: unexpected municipality code={code6!r}"
            )

        out = blank_row(schema)

        out.update({
            "全国地方公共団体コード": code6,
            "ID": RowSupport.clean(row.get("NO")),
            "地方公共団体名": RowSupport.clean(row.get("市区町村名")),
            "名称": RowSupport.clean(row.get("名称")),
            "名称_カナ": RowSupport.clean(row.get("名称_カナ")),
            "名称_英語": RowSupport.clean(row.get("名称_英語")),

            "所在地_全国地方公共団体コード": code6,
            "所在地_連結表記": RowSupport.clean(row.get("住所")),
            "所在地_都道府県": RowSupport.clean(row.get("都道府県名")),
            "所在地_市区町村": RowSupport.clean(row.get("市区町村名")),
            "建物名等(方書)": RowSupport.clean(row.get("方書")),
            "設置位置": RowSupport.clean(row.get("設置位置")),

            "緯度": RowSupport.clean(row.get("緯度")),
            "経度": RowSupport.clean(row.get("経度")),

            "男性トイレ総数": RowSupport.clean(row.get("男性トイレ総数")),
            "男性トイレ数（小便器）":
                RowSupport.clean(row.get("男性トイレ数（小便器）")),
            "男性トイレ数（和式）":
                RowSupport.clean(row.get("男性トイレ数（和式）")),
            "男性トイレ数（洋式）":
                RowSupport.clean(row.get("男性トイレ数（洋式）")),

            "女性トイレ総数": RowSupport.clean(row.get("女性トイレ総数")),
            "女性トイレ数（和式）":
                RowSupport.clean(row.get("女性トイレ数（和式）")),
            "女性トイレ数（洋式）":
                RowSupport.clean(row.get("女性トイレ数（洋式）")),

            "男女共用トイレ総数":
                RowSupport.clean(row.get("男女共用トイレ総数")),
            "男女共用トイレ数（和式）":
                RowSupport.clean(row.get("男女共用トイレ数（和式）")),
            "男女共用トイレ数（洋式）":
                RowSupport.clean(row.get("男女共用トイレ数（洋式）")),

            "車椅子使用者用トイレ有無":
                RowSupport.clean(row.get("車椅子使用者用トイレ有無")),
            "乳幼児用設備設置トイレ有無":
                RowSupport.clean(row.get("乳幼児用設備設置トイレ有無")),
            "オストメイト設置トイレ有無":
                RowSupport.clean(row.get("オストメイト設置トイレ有無")),

            "利用開始時間": RowSupport.clean(row.get("利用開始時間")),
            "利用終了時間": RowSupport.clean(row.get("利用終了時間")),
            "利用可能時間特記事項":
                RowSupport.clean(row.get("利用可能時間特記事項")),

            "画像": RowSupport.clean(row.get("画像")),
            "画像_ライセンス": RowSupport.clean(row.get("画像_ライセンス")),
            "備考": RowSupport.clean(row.get("備考")),
        })

        multipurpose = RowSupport.clean(row.get("多機能トイレ数"))
        if multipurpose:
            # 多機能トイレ数はバリアフリートイレ数へ置換しない。
            RowSupport.append_note(out, f"原データ多機能トイレ数={multipurpose}")

        if not out["ID"]:
            raise RuntimeError(f"斑鳩町 line {line_no}: blank ID")

        if not out["名称"]:
            raise RuntimeError(
                f"斑鳩町 line {line_no}: blank 名称 ID={out['ID']}"
            )

        out_rows.append(out)

    if not out_rows:
        raise RuntimeError("斑鳩町: source produced no data rows")

    StandardCsvWriter().write(dst, schema, out_rows)
    print(f"斑鳩町: {len(out_rows)}")


TARGETS = {
    "23229": normalize_toyoake,
    "29344": normalize_ikaruga,
}


def main() -> int:
    schema = read_schema()

    for func in TARGETS.values():
        func(schema)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
