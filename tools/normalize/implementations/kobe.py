#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from tools.normalize.core.normalization import (
    RowSupport,
    Sha256StableIdStrategy,
    StandardCsvWriter,
)
from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.shapefile import read_point_shapefile_zip


ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"
SOURCE = (
    ROOT
    / "data/raw/28-兵庫県/28100-神戸市/public-toilet/"
    "shimintoilet_opendata_634.zip"
)
DEST = (
    ROOT
    / "data/normalized/28-兵庫県/28100-神戸市/public-toilet/public-toilet.csv"
)

TARGETS = {"28100": "神戸市"}
CODE6 = "281000"
EXPECTED_FIELDS = {"施設名", "住所"}
_ID_STRATEGY = Sha256StableIdStrategy(
    digest_length=12,
    template="{code}-SRC-{digest}",
)
_WRITER = StandardCsvWriter()


def format_coordinate(value: float) -> str:
    return repr(float(value))


def main() -> None:
    if "28100" not in TARGETS:
        return
    if DEST.exists():
        raise RuntimeError(f"28100: normalized already exists: {DEST}")

    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    source_rows = read_point_shapefile_zip(SOURCE, encoding="cp932")
    if not source_rows:
        raise RuntimeError("28100: no source rows")

    normalized: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    seen_addresses: set[str] = set()

    for index, source in enumerate(source_rows, start=1):
        fields = set(source.attributes)
        if fields != EXPECTED_FIELDS:
            raise RuntimeError(
                f"28100: record {index}: unexpected fields: {sorted(fields)!r}"
            )

        name = source.attributes["施設名"]
        address = source.attributes["住所"]
        if not name or not address:
            raise RuntimeError(
                f"28100: record {index}: missing name/address: "
                f"{source.attributes!r}"
            )

        if name in seen_names:
            raise RuntimeError(f"28100: duplicate source name: {name!r}")
        if address in seen_addresses:
            raise RuntimeError(f"28100: duplicate source address: {address!r}")
        seen_names.add(name)
        seen_addresses.add(address)

        ident = _ID_STRATEGY.generate("28100", name, address)
        if ident in seen_ids:
            raise RuntimeError(f"28100: generated duplicate ID: {ident}")
        seen_ids.add(ident)

        row = {field: "" for field in schema}
        row["全国地方公共団体コード"] = CODE6
        row["ID"] = ident
        row["地方公共団体名"] = "兵庫県神戸市"
        row["名称"] = name
        row["所在地_全国地方公共団体コード"] = CODE6
        row["所在地_連結表記"] = f"兵庫県神戸市{address}"
        row["所在地_都道府県"] = "兵庫県"
        row["所在地_市区町村"] = "神戸市"
        row["緯度"] = format_coordinate(source.latitude)
        row["経度"] = format_coordinate(source.longitude)

        RowSupport.append_note(
            row,
            "原データにID項目なし。施設名・住所から決定的IDを生成",
        )
        normalized.append(row)

    _WRITER.write(DEST, schema, normalized)

    print(
        "OK 28100 神戸市: "
        f"rows={len(normalized)} source=shape encoding=cp932 "
        f"generated_ids={len(normalized)}"
    )


if __name__ == "__main__":
    main()
