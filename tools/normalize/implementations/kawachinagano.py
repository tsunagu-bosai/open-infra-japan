#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

from tools.normalize.core.normalization import (
    RowSupport,
    Sha256StableIdStrategy,
    StandardCsvWriter,
)
from tools.normalize.core.schema import read_schema_fields

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

CODE = "27216"
CODE6 = "272167"
NAME = "河内長野市"
PREF = "大阪府"
PREF_DIR = "27-大阪府"
MUN_DIR = "27216-河内長野市"
SOURCE_FILE = "27216_public-toilet.csv"

EXPECTED_HEADER = [
    "名称",
    "名称カナ",
    "住所",
    "設置位置",
    "緯度",
    "経度",
    "男性トイレ総数",
    "女性トイレ総数",
    "男女共用トイレ総数",
    "多機能トイレ数",
    "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無",
    "利用開始時間",
    "利用終了時間",
]


_ID_STRATEGY = Sha256StableIdStrategy(template="{code}-{digest}")
_WRITER = StandardCsvWriter()

def normalize_yes_no(value: object) -> str:
    text = RowSupport.clean(value)
    if text in {"有", "有り", "あり"}:
        return "有"
    if text in {"無", "無し", "なし"}:
        return "無"
    return text



def read_source(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != EXPECTED_HEADER:
            raise RuntimeError(
                f"{path}: header mismatch\n"
                f"actual={reader.fieldnames!r}\n"
                f"expected={EXPECTED_HEADER!r}"
            )

        rows: list[dict[str, str]] = []
        for line_no, source in enumerate(reader, 2):
            if None in source:
                raise RuntimeError(
                    f"{path}:{line_no}: overflow columns={source[None]!r}"
                )
            row = {key: RowSupport.clean(value) for key, value in source.items()}
            if any(row.values()):
                rows.append(row)

    if not rows:
        raise RuntimeError(f"{path}: no data rows")
    return rows


def prepare() -> tuple[Path, list[str], list[dict[str, str]]]:
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"{SCHEMA_PATH}: schema columns={len(schema)} expected=39")

    source_path = (
        ROOT / "data/raw" / PREF_DIR / MUN_DIR / "public-toilet" / SOURCE_FILE
    )
    dest = (
        ROOT / "data/normalized" / PREF_DIR / MUN_DIR
        / "public-toilet" / "public-toilet.csv"
    )

    source_rows = read_source(source_path)
    rows: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    for line_no, source in enumerate(source_rows, 2):
        name = source["名称"]
        address = source["住所"]
        position = source["設置位置"]
        lat = source["緯度"]
        lon = source["経度"]

        if not name:
            raise RuntimeError(f"{source_path}:{line_no}: blank 名称")
        if not lat or not lon:
            raise RuntimeError(
                f"{source_path}:{line_no}: blank coordinates lat={lat!r} lon={lon!r}"
            )

        row = {field: "" for field in schema}
        row["全国地方公共団体コード"] = CODE6
        row["所在地_全国地方公共団体コード"] = CODE6
        row["地方公共団体名"] = NAME
        row["名称"] = name
        row["名称_カナ"] = source["名称カナ"]
        row["所在地_連結表記"] = f"{PREF}{NAME}{address}" if address else ""
        row["所在地_都道府県"] = PREF
        row["所在地_市区町村"] = NAME
        row["所在地_番地以下"] = address
        row["設置位置"] = position
        row["緯度"] = lat
        row["経度"] = lon
        row["車椅子使用者用トイレ有無"] = normalize_yes_no(
            source["車椅子使用者用トイレ有無"]
        )
        row["乳幼児用設備設置トイレ有無"] = normalize_yes_no(
            source["乳幼児用設備設置トイレ有無"]
        )
        row["オストメイト設置トイレ有無"] = normalize_yes_no(
            source["オストメイト設置トイレ有無"]
        )
        row["利用開始時間"] = source["利用開始時間"]
        row["利用終了時間"] = source["利用終了時間"]

        row["ID"] = _ID_STRATEGY.generate(CODE, name, address, position, lat, lon)
        if row["ID"] in seen_ids:
            raise RuntimeError(
                f"{source_path}:{line_no}: duplicate generated ID={row['ID']}"
            )
        seen_ids.add(row["ID"])

        # 便器数は文章形式で、幼児用便器を含む等の表記揺れがあるため、
        # 標準の数値列へ推測変換せず原文を保持する。
        RowSupport.append_labeled_note(row, "原データ男性トイレ総数", source["男性トイレ総数"])
        RowSupport.append_labeled_note(row, "原データ女性トイレ総数", source["女性トイレ総数"])
        RowSupport.append_labeled_note(row, "原データ男女共用トイレ総数", source["男女共用トイレ総数"])
        RowSupport.append_labeled_note(row, "原データ多機能トイレ数", source["多機能トイレ数"])

        rows.append(row)

    return dest, schema, rows



def main() -> None:
    dest, schema, rows = prepare()
    print(f"preflight OK: {CODE} {NAME} rows={len(rows)}")
    _WRITER.write(dest, schema, rows)
    print(f"OK {CODE} {NAME}: rows={len(rows)} source={SOURCE_FILE}")


if __name__ == "__main__":
    main()
