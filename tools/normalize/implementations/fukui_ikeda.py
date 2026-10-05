#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from pathlib import Path

from tools import normalize_public_toilet as common
from tools.normalize.core.normalization import (
    AllowedValueStrategy,
    RowSupport,
    Sha256StableIdStrategy,
    StandardCsvWriter,
    StrictHmsTimeStrategy,
)

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "data/raw/18-福井県/18382-池田町/public-toilet/18382_public-toilet.csv"
OUTPUT = ROOT / "data/normalized/18-福井県/18382-池田町/public-toilet/public-toilet.csv"
SCHEMA = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {"18382": "池田町"}
ID_STRATEGY = Sha256StableIdStrategy(digest_length=12)
CODE6 = "183822"

EXPECTED_HEADER = [
    "施設名", "施設名(英語)", "男性トイレ数", "女性トイレ数",
    "男女共用トイレ数", "バリアフリートイレ数",
    "ベビーベッド(有、無)", "オストメイト(有、無)",
    "利用可能時間OPENS", "利用可能時間CLOSES",
    "説明(日本語)", "説明(英語)", "緯度", "経度",
    "画像URL", "画像URL", "画像URL", "画像URL",
]



def read_schema() -> list[str]:
    with SCHEMA.open("r", encoding="utf-8-sig", newline="") as f:
        return [row["name"] for row in csv.DictReader(f)]




TIME_NORMALIZER = StrictHmsTimeStrategy()
BOOLEAN_NORMALIZER = AllowedValueStrategy(("", "有", "無"), cleaner=RowSupport.clean)


def validate_numeric(value: str, field: str) -> str:
    value = RowSupport.clean(value)
    if value and not value.isdigit():
        raise RuntimeError(f"{field}: non-numeric value {value!r}")
    return value



def main() -> None:
    if "18382" not in TARGETS:
        return
    if OUTPUT.exists():
        raise RuntimeError(f"18382: normalized already exists: {OUTPUT}")

    schema = read_schema()
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    with SOURCE.open("r", encoding="cp932", newline="") as f:
        physical = list(csv.reader(f))

    if not physical:
        raise RuntimeError("empty source")
    if physical[0] != EXPECTED_HEADER:
        raise RuntimeError(f"unexpected header: {physical[0]!r}")

    source_rows = [row for row in physical[1:] if any(RowSupport.clean(v) for v in row)]
    if not source_rows:
        raise RuntimeError("source contains no meaningful data rows")
    if any(len(row) != 18 for row in source_rows):
        raise RuntimeError("source contains malformed row width")

    normalized = []
    seen_ids: set[str] = set()

    for source in source_rows:
        row = {field: "" for field in schema}

        name = RowSupport.clean(source[0])
        lat = RowSupport.clean(source[12])
        lon = RowSupport.clean(source[13])
        if not name or not lat or not lon:
            raise RuntimeError(f"required source value missing: {source!r}")

        ident = ID_STRATEGY.generate("18382", name, lat, lon)
        if ident in seen_ids:
            raise RuntimeError(f"generated duplicate ID: {ident}")
        seen_ids.add(ident)

        # Coordinate validation only; retain source precision/text.
        try:
            lat_num, lon_num = float(lat), float(lon)
        except ValueError as exc:
            raise RuntimeError(f"invalid coordinate: {lat!r}, {lon!r}") from exc
        if not (-90 <= lat_num <= 90 and -180 <= lon_num <= 180):
            raise RuntimeError(f"out-of-range coordinate: {lat!r}, {lon!r}")

        row["全国地方公共団体コード"] = CODE6
        row["ID"] = ident
        row["地方公共団体名"] = "福井県池田町"
        row["名称"] = name
        row["名称_英語"] = RowSupport.clean(source[1])
        row["所在地_全国地方公共団体コード"] = CODE6
        row["所在地_都道府県"] = "福井県"
        row["所在地_市区町村"] = "池田町"
        row["緯度"] = lat
        row["経度"] = lon

        row["男性トイレ総数"] = validate_numeric(source[2], "男性トイレ数")
        row["女性トイレ総数"] = validate_numeric(source[3], "女性トイレ数")
        row["男女共用トイレ総数"] = validate_numeric(source[4], "男女共用トイレ数")
        row["バリアフリートイレ数"] = validate_numeric(source[5], "バリアフリートイレ数")
        row["乳幼児用設備設置トイレ有無"] = BOOLEAN_NORMALIZER(
            source[6], "ベビーベッド(有、無)"
        )
        row["オストメイト設置トイレ有無"] = BOOLEAN_NORMALIZER(
            source[7], "オストメイト(有、無)"
        )
        row["利用開始時間"] = TIME_NORMALIZER(source[8])
        row["利用終了時間"] = TIME_NORMALIZER(source[9])
        row["利用可能時間特記事項"] = RowSupport.clean(source[10])

        if RowSupport.clean(source[11]):
            RowSupport.append_note(row, f"原データ説明(英語)={RowSupport.clean(source[11])}")

        images = []
        for value in source[14:18]:
            value = RowSupport.clean(value)
            if value and value not in images:
                images.append(value)
        if images:
            row["画像"] = images[0]
            for extra in images[1:]:
                RowSupport.append_note(row, f"追加画像URL={extra}")

        RowSupport.append_note(
            row,
            "原データにID項目なし。施設名・緯度・経度から決定的IDを生成"
        )
        normalized.append(row)

    patches = common.load_patches("18-福井県", "18382-池田町")
    applied, problems = common.apply_patches(normalized, patches, SOURCE)
    if problems:
        raise RuntimeError(
            "18382-池田町: patch適用失敗: " + " | ".join(map(str, problems))
        )

    StandardCsvWriter().write(OUTPUT, schema, normalized)

    print(
        f"OK 18382 池田町: rows={len(normalized)} "
        f"generated_ids={len(normalized)} patches={applied}"
    )


if __name__ == "__main__":
    main()
