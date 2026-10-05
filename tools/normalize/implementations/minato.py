#!/usr/bin/env python3
from __future__ import annotations

import json
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

CODE = "13103"
NAME = "港区"
PREF = "東京都"
PREF_DIR = "13-東京都"
MUN_DIR = "13103-港区"
SOURCE_FILE = "13103_public-toilet.geojson"
EXPECTED_PROPERTIES = {"名称", "所在地", "開設年月日"}


_ID_STRATEGY = Sha256StableIdStrategy(template="{code}-{digest}")
_WRITER = StandardCsvWriter()

def load_features(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))

    if data.get("type") != "FeatureCollection":
        raise RuntimeError(f"{path}: type={data.get('type')!r} expected='FeatureCollection'")

    features = data.get("features")
    if not isinstance(features, list):
        raise RuntimeError(f"{path}: features is not a list")
    if not features:
        raise RuntimeError(f"{path}: no features")

    return features


def prepare() -> tuple[Path, list[str], list[dict[str, str]]]:
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"{SCHEMA_PATH}: schema columns={len(schema)} expected=39")

    source = ROOT / "data/raw" / PREF_DIR / MUN_DIR / "public-toilet" / SOURCE_FILE
    dest = (
        ROOT / "data/normalized" / PREF_DIR / MUN_DIR
        / "public-toilet" / "public-toilet.csv"
    )

    features = load_features(source)
    code6 = six_digit_municipality_code(CODE)
    rows: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    for index, feature in enumerate(features, 1):
        if feature.get("type") != "Feature":
            raise RuntimeError(f"{source}: feature {index}: type={feature.get('type')!r}")

        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "Point":
            raise RuntimeError(
                f"{source}: feature {index}: geometry type={geometry.get('type')!r}"
            )

        coords = geometry.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2:
            raise RuntimeError(
                f"{source}: feature {index}: invalid coordinates={coords!r}"
            )

        lon = RowSupport.clean(coords[0])
        lat = RowSupport.clean(coords[1])
        if not lon or not lat:
            raise RuntimeError(
                f"{source}: feature {index}: blank coordinates lon={lon!r} lat={lat!r}"
            )

        props = feature.get("properties") or {}
        if set(props.keys()) != EXPECTED_PROPERTIES:
            raise RuntimeError(
                f"{source}: feature {index}: properties={set(props.keys())!r} "
                f"expected={EXPECTED_PROPERTIES!r}"
            )

        name = RowSupport.clean(props.get("名称"))
        address = RowSupport.clean(props.get("所在地"))
        opened = RowSupport.clean(props.get("開設年月日"))

        if not name:
            raise RuntimeError(f"{source}: feature {index}: blank 名称")
        if not address:
            raise RuntimeError(f"{source}: feature {index}: blank 所在地")

        row = {field: "" for field in schema}
        row["全国地方公共団体コード"] = code6
        row["所在地_全国地方公共団体コード"] = code6
        row["地方公共団体名"] = NAME
        row["名称"] = name
        row["所在地_連結表記"] = address
        row["所在地_都道府県"] = PREF
        row["所在地_市区町村"] = NAME
        row["緯度"] = lat
        row["経度"] = lon
        row["ID"] = _ID_STRATEGY.generate(CODE, name, address, lat, lon)

        if row["ID"] in seen_ids:
            raise RuntimeError(f"{source}: feature {index}: duplicate generated ID={row['ID']}")
        seen_ids.add(row["ID"])

        if opened:
            RowSupport.append_note(row, f"原データ開設年月日={opened}")

        rows.append(row)

    return dest, schema, rows



def main() -> None:
    dest, schema, rows = prepare()
    print(f"preflight OK: {CODE} {NAME} rows={len(rows)}")
    _WRITER.write(dest, schema, rows)
    print(f"OK {CODE} {NAME}: rows={len(rows)} source={SOURCE_FILE}")


if __name__ == "__main__":
    main()
