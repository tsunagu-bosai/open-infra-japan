#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path

import xlrd

from tools.normalize.core.normalization import (
    RowSupport,
    Sha256StableIdStrategy,
    StandardCsvWriter,
)
from tools.normalize.core.schema import read_schema_fields


ROOT = Path.cwd()
RAW = ROOT / "data/raw/42-長崎県/42202-佐世保市/public-toilet"
OUT = ROOT / "data/normalized/42-長崎県/42202-佐世保市/public-toilet/public-toilet.csv"
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {"42202-佐世保市"}

CODE6 = "422029"
MUNICIPALITY = "佐世保市"
PREFECTURE = "長崎県"

CSV_PATH = RAW / "toire_5_4326wgs84.csv"
GEOJSON_PATH = RAW / "toire_4_4326wgs84.geojson"
XLS_PATH = RAW / "2c62c341-40b0-43da-8200-0346d234f7db.xls"


_ID_STRATEGY = Sha256StableIdStrategy(
    digest_length=16,
    template="42202-{code}-{digest}",
)
_WRITER = StandardCsvWriter()


def base_row(schema: list[str]) -> dict[str, str]:
    row = {field: "" for field in schema}
    row["全国地方公共団体コード"] = CODE6
    row["地方公共団体名"] = MUNICIPALITY
    row["所在地_全国地方公共団体コード"] = CODE6
    row["所在地_都道府県"] = PREFECTURE
    row["所在地_市区町村"] = MUNICIPALITY
    return row


def read_csv_rows() -> list[dict[str, str]]:
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = [
            {RowSupport.clean(k): RowSupport.clean(v) for k, v in source.items()}
            for source in reader
            if RowSupport.has_meaningful_value(source.values())
        ]

    if not rows:
        raise RuntimeError("CSV has no data rows")

    expected = {"番号", "名前", "住所", "トイレ�"}
    if set(reader.fieldnames or []) != expected:
        raise RuntimeError(
            f"unexpected CSV header: {reader.fieldnames!r}"
        )

    return rows


def read_geo_features() -> list[dict]:
    data = json.loads(GEOJSON_PATH.read_text(encoding="utf-8-sig"))
    if data.get("type") != "FeatureCollection":
        raise RuntimeError(f"unexpected GeoJSON type={data.get('type')!r}")

    features = data.get("features") or []
    if not features:
        raise RuntimeError("GeoJSON has no features")

    return features


def normalize_geo(schema: list[str]) -> list[dict[str, str]]:
    csv_rows = read_csv_rows()
    features = read_geo_features()

    if len(csv_rows) != len(features):
        raise RuntimeError(
            f"CSV/GeoJSON row-count mismatch: csv={len(csv_rows)} "
            f"geojson={len(features)}"
        )

    out: list[dict[str, str]] = []

    for index, (source, feature) in enumerate(zip(csv_rows, features), 1):
        properties = {
            RowSupport.clean(k): RowSupport.clean(v)
            for k, v in (feature.get("properties") or {}).items()
        }

        csv_key = (
            source["番号"],
            source["名前"],
            source["住所"],
        )
        geo_key = (
            properties.get("番号", ""),
            properties.get("名前", ""),
            properties.get("住所", ""),
        )
        if csv_key != geo_key:
            raise RuntimeError(
                f"CSV/GeoJSON mismatch at row {index}: "
                f"csv={csv_key!r} geo={geo_key!r}"
            )

        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if geometry.get("type") != "Point" or len(coordinates) < 2:
            raise RuntimeError(
                f"invalid geometry at row {index}: {geometry!r}"
            )

        lon = RowSupport.clean(coordinates[0])
        lat = RowSupport.clean(coordinates[1])
        name = source["名前"]
        address = source["住所"]

        if not name or not address or not lat or not lon:
            raise RuntimeError(
                f"row {index}: required GEO source value is blank"
            )

        row = base_row(schema)
        row["ID"] = _ID_STRATEGY.generate(
            "GEO",
            source["番号"],
            name,
            address,
            lat,
            lon,
        )
        row["名称"] = name
        row["所在地_連結表記"] = (
            address if address.startswith(PREFECTURE)
            else f"{PREFECTURE}{MUNICIPALITY}{address}"
        )
        row["緯度"] = lat
        row["経度"] = lon

        RowSupport.append_note(row, f"原データ番号={source['番号']}")
        if source.get("トイレ�"):
            RowSupport.append_note(row, f"原データトイレ�={source['トイレ�']}")

        out.append(row)

    full_keys = [
        (
            source["番号"],
            source["名前"],
            source["住所"],
        )
        for source in csv_rows
    ]
    if len(full_keys) != len(set(full_keys)):
        raise RuntimeError("duplicate GEO full keys")

    return out


def normalize_xls(schema: list[str]) -> list[dict[str, str]]:
    book = xlrd.open_workbook(XLS_PATH)
    if book.nsheets != 1:
        raise RuntimeError(f"XLS sheets={book.nsheets} expected=1")

    sheet = book.sheet_by_index(0)
    if sheet.name != "事業概要（原稿）":
        raise RuntimeError(f"unexpected XLS sheet={sheet.name!r}")

    out: list[dict[str, str]] = []

    for row_index in range(3, sheet.nrows):
        number_raw = sheet.cell_value(row_index, 1)
        name = RowSupport.clean(sheet.cell_value(row_index, 2))
        address = RowSupport.clean(sheet.cell_value(row_index, 3))
        year = RowSupport.clean(sheet.cell_value(row_index, 4))
        area = RowSupport.clean(sheet.cell_value(row_index, 5))
        structure = RowSupport.clean(sheet.cell_value(row_index, 7))
        treatment = RowSupport.clean(sheet.cell_value(row_index, 8))

        if not name:
            continue
        if not address:
            raise RuntimeError(
                f"XLS row {row_index + 1}: blank address"
            )

        if isinstance(number_raw, float) and number_raw.is_integer():
            number = str(int(number_raw))
        else:
            number = RowSupport.clean(number_raw)

        row = base_row(schema)
        row["ID"] = _ID_STRATEGY.generate("XLS", number, name, address)
        row["名称"] = name
        row["所在地_連結表記"] = f"{PREFECTURE}{MUNICIPALITY}{address}"

        RowSupport.append_note(row, f"原データ番号={number}")
        RowSupport.append_note(row, f"原データ建設年={year}")
        RowSupport.append_note(row, f"原データ面積(㎡)={area}")
        RowSupport.append_note(row, f"原データ構造={structure}")
        RowSupport.append_note(row, f"原データ処理方式={treatment}")

        out.append(row)

    if not out:
        raise RuntimeError("XLS has no data rows")

    return out


def main() -> None:
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    for path in (CSV_PATH, GEOJSON_PATH, XLS_PATH):
        if not path.exists():
            raise RuntimeError(f"missing raw: {path}")

    if OUT.exists():
        raise RuntimeError(f"normalized already exists: {OUT}")

    geo_rows = normalize_geo(schema)
    xls_rows = normalize_xls(schema)
    rows = [*geo_rows, *xls_rows]

    if not rows:
        raise RuntimeError("no normalized rows")

    ids = [row["ID"] for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate IDs")

    _WRITER.write(OUT, schema, rows)

    print(
        f"42202-佐世保市 geo={len(geo_rows)} "
        f"xls={len(xls_rows)} total={len(rows)}"
    )


if __name__ == "__main__":
    main()
