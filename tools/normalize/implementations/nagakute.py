#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from pathlib import Path

from tools import normalize_public_toilet as common
from tools.normalize.core.normalization import (
    RowSupport,
    StandardCsvWriter,
    StrictEndOfDayTimeStrategy,
)

ROOT = Path(__file__).resolve().parents[3]
RAW = (
    ROOT
    / "data/raw/23-愛知県/23238-長久手市/public-toilet"
    / "232386_15_kousyuutoireitiran_20260713_1112.csv"
)
OUT = (
    ROOT
    / "data/normalized/23-愛知県/23238-長久手市/public-toilet/public-toilet.csv"
)
SCHEMA = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {"23238": "長久手市"}

EXPECTED_HEADER = [
    "都道府県コード又は市区町村コード", "NO", "都道府県名", "市区町村名",
    "名称", "名称_カナ", "名称_英語", "住所", "方書", "設置位置", "緯度", "経度",
    "男性トイレ総数", "男性トイレ数（小便器）", "男性トイレ数（和式）",
    "男性トイレ数（洋式）", "女性トイレ総数", "女性トイレ数（和式）",
    "女性トイレ数（洋式）", "男女共用トイレ総数", "男女共用トイレ数（和式）",
    "男女共用トイレ数（洋式）", "多機能トイレ数",
    "車椅子使用者用トイレ有無", "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無", "利用開始時間", "利用終了時間",
    "利用可能日時特記事項", "画像", "画像_ライセンス", "備考",
]

DIRECT = {
    "NO": "ID",
    "名称": "名称",
    "名称_カナ": "名称_カナ",
    "名称_英語": "名称_英語",
    "住所": "所在地_連結表記",
    "都道府県名": "所在地_都道府県",
    "市区町村名": "所在地_市区町村",
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
    "画像": "画像",
    "画像_ライセンス": "画像_ライセンス",
    "備考": "備考",
}



def read_schema() -> list[str]:
    with SCHEMA.open("r", encoding="utf-8-sig", newline="") as f:
        return [r["name"] for r in csv.DictReader(f)]


TIME_NORMALIZER = StrictEndOfDayTimeStrategy()


def repair_rows(rows: list[list[str]]) -> list[list[str]]:
    repaired: list[list[str]] = []
    i = 0
    address_repaired = 0
    split_repaired = 0

    while i < len(rows):
        row = rows[i]

        if len(row) == 32:
            repaired.append(row)
            i += 1
            continue

        if (
            len(row) == 36
            and row[1].strip() == "1500000041"
            and row[4].strip() == "一ノ井１号公園"
        ):
            address = ",".join(x.strip() for x in row[7:12] if x.strip())
            fixed = row[:7] + [address] + row[12:]
            if len(fixed) != 32:
                raise RuntimeError(
                    f"一ノ井１号公園の住所修復後列数={len(fixed)} expected=32"
                )
            repaired.append(fixed)
            address_repaired += 1
            i += 1
            continue

        if (
            len(row) == 29
            and row[1].strip() == "1500000065"
            and row[4].strip() == "長久手市文化の家"
        ):
            if i + 1 >= len(rows):
                raise RuntimeError("長久手市文化の家の継続行がありません")
            continuation = rows[i + 1]
            if (
                len(continuation) != 4
                or continuation[0].strip() != "（月曜日が祝日の場合は翌平日）"
            ):
                raise RuntimeError(
                    f"長久手市文化の家の継続行が想定外です: {continuation!r}"
                )

            fixed = list(row)
            fixed[28] = fixed[28].strip() + continuation[0].strip()
            fixed.extend(continuation[1:4])

            if len(fixed) != 32:
                raise RuntimeError(
                    f"長久手市文化の家の修復後列数={len(fixed)} expected=32"
                )

            repaired.append(fixed)
            split_repaired += 1
            i += 2
            continue

        raise RuntimeError(
            f"未対応の壊れた行があります: columns={len(row)} row={row!r}"
        )

    if address_repaired != 1 or split_repaired != 1:
        raise RuntimeError(
            f"修復件数が想定外です: address={address_repaired} "
            f"multiline={split_repaired}"
        )
    if not repaired:
        raise RuntimeError("修復後のデータ行がありません")

    return repaired



def main() -> None:
    if "23238" not in TARGETS:
        return

    if OUT.exists():
        raise RuntimeError(f"23238: normalized already exists: {OUT}")

    schema = read_schema()
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    with RAW.open("r", encoding="utf-8-sig", newline="") as f:
        physical = list(csv.reader(f))

    if not physical:
        raise RuntimeError("empty source")
    if physical[0] != EXPECTED_HEADER:
        raise RuntimeError(f"unexpected source header: {physical[0]!r}")
    rows = repair_rows(physical[1:])
    source_rows = [dict(zip(EXPECTED_HEADER, row)) for row in rows]

    normalized: list[dict[str, str]] = []
    multifunctional_preserved = 0
    end_24_corrected = 0

    for source in source_rows:
        source = {k: (v or "").strip() for k, v in source.items()}
        row = {k: "" for k in schema}

        if source["都道府県コード又は市区町村コード"] != "23238":
            raise RuntimeError(
                "unexpected municipality code="
                f"{source['都道府県コード又は市区町村コード']!r}"
            )

        row["全国地方公共団体コード"] = "232386"
        row["地方公共団体名"] = "長久手市"
        row["所在地_全国地方公共団体コード"] = "232386"

        for source_field, target_field in DIRECT.items():
            row[target_field] = source[source_field]

        for field in (
            "車椅子使用者用トイレ有無",
            "乳幼児用設備設置トイレ有無",
            "オストメイト設置トイレ有無",
        ):
            if row[field] not in ("", "有", "無"):
                raise RuntimeError(
                    f"unexpected boolean {field}={row[field]!r}"
                )

        multifunctional = source["多機能トイレ数"]
        if multifunctional:
            RowSupport.append_note(
                row,
                f"原データ多機能トイレ数={multifunctional}",
            )
            multifunctional_preserved += 1

        row["利用開始時間"] = TIME_NORMALIZER(
            source["利用開始時間"], row, "利用開始時間"
        )
        row["利用終了時間"] = TIME_NORMALIZER(
            source["利用終了時間"], row, "利用終了時間"
        )
        if source["利用終了時間"] == "24:00":
            end_24_corrected += 1

        row["利用可能時間特記事項"] = source["利用可能日時特記事項"]
        normalized.append(row)

    ids = [row["ID"] for row in normalized]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise RuntimeError("NO must be populated and unique after repair")

    patches = common.load_patches("23-愛知県", "23238-長久手市")
    applied, problems = common.apply_patches(normalized, patches, RAW)
    if problems:
        raise RuntimeError(
            "23238-長久手市: patch適用失敗: " + " | ".join(map(str, problems))
        )

    StandardCsvWriter().write(OUT, schema, normalized)

    print("preflight OK: 長久手市")
    print(
        f"OK 23238 長久手市: rows={len(normalized)} code=232386 "
        f"malformed_address_repaired=1 multiline_record_repaired=1 "
        f"multifunctional_preserved={multifunctional_preserved} "
        f"end_24_corrected={end_24_corrected} patches={applied}"
    )


if __name__ == "__main__":
    main()
