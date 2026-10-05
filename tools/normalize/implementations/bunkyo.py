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
RAW = ROOT / "data/raw/13-東京都/13105-文京区/public-toilet/kunaikosyubenjyo.csv"
OUT = ROOT / "data/normalized/13-東京都/13105-文京区/public-toilet/public-toilet.csv"
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {"13105-文京区"}
CODE6 = "131059"
MUNICIPALITY = "文京区"
PREFECTURE = "東京都"

EXPECTED_HEADER_PREFIX = [
    "公衆便所名", "住所", "緯度", "経度", "建物面積（m2）", "敷地面積（m2）",
    "設置年", "改築年", "身障者用便所", "説明（日本語）",
    "車椅子使用者用トイレ有無", "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無",
]

_ID_STRATEGY = Sha256StableIdStrategy(template="{code}-{digest}")
_WRITER = StandardCsvWriter()

def add_note(parts, label, value):
    value = RowSupport.clean(value)
    if value:
        parts.append(f"{label}={value}")

def main():
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")
    if not RAW.exists():
        raise RuntimeError(f"missing raw: {RAW}")
    if OUT.exists():
        raise RuntimeError(f"normalized already exists: {OUT}")

    with RAW.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            raise RuntimeError("empty source")
        header = [RowSupport.clean(v) for v in header]
        if header[:13] != EXPECTED_HEADER_PREFIX:
            raise RuntimeError(f"unexpected header prefix: actual={header[:13]!r}")

        rows = []
        for line_no, physical in enumerate(reader, 2):
            values = [RowSupport.clean(v) for v in physical]
            if not any(values[:13]):
                continue
            if len(values) < 13:
                raise RuntimeError(f"line {line_no}: columns={len(values)} expected>=13")

            (name, address, lat, lon, building_area, site_area, installed_year,
             rebuilt_year, disabled_toilet, description, wheelchair, infant,
             ostomate) = values[:13]

            if not name:
                raise RuntimeError(f"line {line_no}: blank name")
            if not address:
                raise RuntimeError(f"line {line_no}: blank address")
            if not lat or not lon:
                raise RuntimeError(f"line {line_no}: blank coordinates")

            row = {field: "" for field in schema}
            row["全国地方公共団体コード"] = CODE6
            row["ID"] = _ID_STRATEGY.generate("13105", name, address, lat, lon)
            row["地方公共団体名"] = MUNICIPALITY
            row["名称"] = name
            row["所在地_全国地方公共団体コード"] = CODE6
            row["所在地_連結表記"] = address
            row["所在地_都道府県"] = PREFECTURE
            row["所在地_市区町村"] = MUNICIPALITY
            row["緯度"] = lat
            row["経度"] = lon
            row["車椅子使用者用トイレ有無"] = wheelchair
            row["乳幼児用設備設置トイレ有無"] = infant
            row["オストメイト設置トイレ有無"] = ostomate

            notes = []
            add_note(notes, "原データ建物面積（m2）", building_area)
            add_note(notes, "原データ敷地面積（m2）", site_area)
            add_note(notes, "原データ設置年", installed_year)
            add_note(notes, "原データ改築年", rebuilt_year)
            add_note(notes, "原データ身障者用便所", disabled_toilet)
            add_note(notes, "原データ説明（日本語）", description)
            row["備考"] = " / ".join(notes)
            rows.append(row)

    if not rows:
        raise RuntimeError("no data rows")
    ids = [row["ID"] for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate IDs")

    _WRITER.write(OUT, schema, rows)

    print(f"13105-文京区 rows={len(rows)} source={RAW.name}")

if __name__ == "__main__":
    main()
