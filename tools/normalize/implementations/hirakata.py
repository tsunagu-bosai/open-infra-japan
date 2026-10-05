#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from pathlib import Path

from tools.normalize.core.normalization import (
    LenientHmsTimeStrategy,
    RowSupport,
    Sha256StableIdStrategy,
    StandardCsvWriter,
)
from tools.normalize.core.schema import read_schema_fields
from tools import normalize_public_toilet as common

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

CODE = "27210"
CODE6 = "272108"
NAME = "枚方市"
PREF = "大阪府"
PREF_DIR = "27-大阪府"
MUN_DIR = "27210-枚方市"
SOURCE_FILE = "27210_public-toilet.csv"

EXPECTED_HEADER = [
    "都道府県名",
    "市区町村名",
    "部署名",
    "公園番号",
    "名称",
    "名称_カナ（全角カナ）",
    "緯度",
    "経度",
    "住所",
    "方書",
    "設置位置",
    "和・洋の種別",
    "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無",
    "おむつ替え台",
    "授乳室",
    "オストメイト設置トイレ有無",
    "利用開始時間",
    "利用終了時間",
    "利用可能時間特記事項",
    "備考",
]

PLACEHOLDERS = {"", "-", "－", "―", "ー"}


_ID_STRATEGY = Sha256StableIdStrategy(template="{code}-{digest}")
_WRITER = StandardCsvWriter()

def clean_placeholder(value: object) -> str:
    text = RowSupport.clean(value)
    return "" if text in PLACEHOLDERS else text


TIME_NORMALIZER = LenientHmsTimeStrategy(cleaner=clean_placeholder)



def read_source(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="cp932", newline="") as f:
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
        if source["都道府県名"] != PREF:
            raise RuntimeError(
                f"{source_path}:{line_no}: 都道府県名={source['都道府県名']!r}"
            )
        if source["市区町村名"] != NAME:
            raise RuntimeError(
                f"{source_path}:{line_no}: 市区町村名={source['市区町村名']!r}"
            )

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
        row["名称_カナ"] = source["名称_カナ（全角カナ）"]
        row["所在地_連結表記"] = address
        row["所在地_都道府県"] = PREF
        row["所在地_市区町村"] = NAME
        row["建物名等(方書)"] = source["方書"]
        row["設置位置"] = position
        row["緯度"] = lat
        row["経度"] = lon
        row["車椅子使用者用トイレ有無"] = clean_placeholder(
            source["車椅子使用者用トイレ有無"]
        )
        row["乳幼児用設備設置トイレ有無"] = clean_placeholder(
            source["乳幼児用設備設置トイレ有無"]
        )
        row["オストメイト設置トイレ有無"] = clean_placeholder(
            source["オストメイト設置トイレ有無"]
        )
        row["利用開始時間"] = TIME_NORMALIZER(source["利用開始時間"])
        row["利用終了時間"] = TIME_NORMALIZER(source["利用終了時間"])
        row["利用可能時間特記事項"] = clean_placeholder(
            source["利用可能時間特記事項"]
        )
        row["備考"] = clean_placeholder(source["備考"])

        row["ID"] = _ID_STRATEGY.generate(CODE, name, address, position, lat, lon)
        if row["ID"] in seen_ids:
            raise RuntimeError(
                f"{source_path}:{line_no}: duplicate generated ID={row['ID']}"
            )
        seen_ids.add(row["ID"])


        _value = clean_placeholder(source["部署名"])
        if _value:
            RowSupport.append_labeled_note(row, "原データ部署名", _value)

        _value = clean_placeholder(source["公園番号"])
        if _value:
            RowSupport.append_labeled_note(row, "原データ公園番号", _value)

        _value = clean_placeholder(source["和・洋の種別"])
        if _value:
            RowSupport.append_labeled_note(row, "原データ和・洋の種別", _value)

        _value = clean_placeholder(source["おむつ替え台"])
        if _value:
            RowSupport.append_labeled_note(row, "原データおむつ替え台", _value)

        _value = clean_placeholder(source["授乳室"])
        if _value:
            RowSupport.append_labeled_note(row, "原データ授乳室", _value)

        rows.append(row)

    return dest, schema, rows



def main() -> None:
    dest, schema, rows = prepare()
    source_path = (
        ROOT / "data/raw" / PREF_DIR / MUN_DIR / "public-toilet" / SOURCE_FILE
    )
    patches = common.load_patches(PREF_DIR, MUN_DIR)
    applied, problems = common.apply_patches(rows, patches, source_path)
    if problems:
        raise RuntimeError("\n".join(problems))

    print(f"preflight OK: {CODE} {NAME} rows={len(rows)}")
    _WRITER.write(dest, schema, rows)
    print(
        f"OK {CODE} {NAME}: rows={len(rows)} source={SOURCE_FILE} "
        f"patches={applied}"
    )


if __name__ == "__main__":
    main()
