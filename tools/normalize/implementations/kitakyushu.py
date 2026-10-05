#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.normalization import (
    RowSupport,
    Sha256StableIdStrategy,
    StandardCsvWriter,
)
from tools.normalize.core.schema import read_schema_fields

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

CODE = "40100"
NAME = "北九州市"
PREF = "福岡県"
PREF_DIR = "40-福岡県"
MUN_DIR = "40100-北九州市"
SOURCE_FILE = "40100_public-toilet.csv"

EXPECTED_HEADER = [
    "施設名",
    "区名",
    "町名",
    "建築年度",
    "築年数",
    "延床面積（㎡）",
    "棟数",
    "複合の状況",
    "主たる施設名",
    "主な構造",
    "耐震診断",
    "耐震補強",
    "建物所有者",
    "所管局",
    "所管課",
    "管理形態",
]


_ID_STRATEGY = Sha256StableIdStrategy(template="{code}-{digest}")
_WRITER = StandardCsvWriter()

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

    code6 = six_digit_municipality_code(CODE)
    source_rows = read_source(source_path)
    rows: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    for line_no, source in enumerate(source_rows, 2):
        facility = source["施設名"]
        ward = source["区名"]
        town = source["町名"]
        primary_facility = source["主たる施設名"]
        built_year = source["建築年度"]

        if not facility or not ward or not town:
            raise RuntimeError(
                f"{source_path}:{line_no}: required value blank "
                f"facility={facility!r} ward={ward!r} town={town!r}"
            )

        row = {field: "" for field in schema}
        row["全国地方公共団体コード"] = code6
        row["所在地_全国地方公共団体コード"] = code6
        row["地方公共団体名"] = NAME
        row["名称"] = facility

        # 元データは区名・町名までで番地や座標を持たない。
        # 推測補完せず、出典にある粒度だけで連結表記を作る。
        row["所在地_連結表記"] = f"{NAME}{ward}{town}"
        row["所在地_都道府県"] = PREF
        row["所在地_市区町村"] = NAME

        row["ID"] = _ID_STRATEGY.generate(
            CODE,
            facility,
            ward,
            town,
            primary_facility,
            built_year,
        )
        if row["ID"] in seen_ids:
            raise RuntimeError(
                f"{source_path}:{line_no}: duplicate generated ID={row['ID']}"
            )
        seen_ids.add(row["ID"])

        # 資産台帳固有項目は標準列へ意味変換せず原文保存。
        RowSupport.append_labeled_note(row, "原データ区名", ward)
        RowSupport.append_labeled_note(row, "原データ町名", town)
        RowSupport.append_labeled_note(row, "原データ建築年度", built_year)
        RowSupport.append_labeled_note(row, "原データ築年数", source["築年数"])
        RowSupport.append_labeled_note(row, "原データ延床面積（㎡）", source["延床面積（㎡）"])
        RowSupport.append_labeled_note(row, "原データ棟数", source["棟数"])
        RowSupport.append_labeled_note(row, "原データ複合の状況", source["複合の状況"])
        RowSupport.append_labeled_note(row, "原データ主たる施設名", primary_facility)
        RowSupport.append_labeled_note(row, "原データ主な構造", source["主な構造"])
        RowSupport.append_labeled_note(row, "原データ耐震診断", source["耐震診断"])
        RowSupport.append_labeled_note(row, "原データ耐震補強", source["耐震補強"])
        RowSupport.append_labeled_note(row, "原データ建物所有者", source["建物所有者"])
        RowSupport.append_labeled_note(row, "原データ所管局", source["所管局"])
        RowSupport.append_labeled_note(row, "原データ所管課", source["所管課"])
        RowSupport.append_labeled_note(row, "原データ管理形態", source["管理形態"])

        rows.append(row)

    return dest, schema, rows



def main() -> None:
    dest, schema, rows = prepare()
    print(f"preflight OK: {CODE} {NAME} rows={len(rows)}")
    _WRITER.write(dest, schema, rows)
    print(f"OK {CODE} {NAME}: rows={len(rows)} source={SOURCE_FILE}")


if __name__ == "__main__":
    main()
