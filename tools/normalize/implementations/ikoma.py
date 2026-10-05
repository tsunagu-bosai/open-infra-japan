#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from pathlib import Path

from tools.normalize.core.normalization import (
    RowSupport,
    Sha256StableIdStrategy,
    StandardCsvWriter,
)
from tools.normalize.core.schema import read_schema_fields

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

CODE = "29209"
CODE6 = "292095"
NAME = "生駒市"
PREF = "奈良県"
PREF_DIR = "29-奈良県"
MUN_DIR = "29209-生駒市"
SOURCE_FILE = "29209_public-toilet.csv"

EXPECTED_HEADER = [
    "Name",
    "Address",
    "Telephone number",
    "Detail description",
    "Business hours",
    "Latitude",
    "Longitude",
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


def extract_simple_hours(text: str) -> tuple[str, str]:
    text = RowSupport.clean(text)
    if not text:
        return "", ""

    if text == "終日":
        return "00:00", "23:59"

    # 注記を含まない単純な HH:MM〜HH:MM のみ標準時刻へ。
    match = re.fullmatch(r"(\d{1,2}:\d{2})[〜～](\d{1,2}:\d{2})", text)
    if not match:
        return "", ""

    def norm(v: str) -> str:
        h, m = v.split(":")
        return f"{int(h):02d}:{int(m):02d}"

    return norm(match.group(1)), norm(match.group(2))


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
        name = source["Name"]
        address = source["Address"]
        detail = source["Detail description"]
        hours = source["Business hours"]
        lat = source["Latitude"]
        lon = source["Longitude"]

        if not name or not lat or not lon:
            raise RuntimeError(
                f"{source_path}:{line_no}: required value blank "
                f"name={name!r} lat={lat!r} lon={lon!r}"
            )

        row = {field: "" for field in schema}
        row["全国地方公共団体コード"] = CODE6
        row["所在地_全国地方公共団体コード"] = CODE6
        row["地方公共団体名"] = NAME
        row["名称"] = name
        row["所在地_連結表記"] = address
        row["所在地_都道府県"] = PREF
        row["所在地_市区町村"] = NAME
        row["緯度"] = lat
        row["経度"] = lon

        start, end = extract_simple_hours(hours)
        row["利用開始時間"] = start
        row["利用終了時間"] = end
        row["利用可能時間特記事項"] = hours

        # 原文に「オストメイト」が明示される場合のみ肯定値を入れる。
        # 記載がない施設を「無」とは推測しない。
        if "オストメイト" in detail:
            row["オストメイト設置トイレ有無"] = "有"

        row["ID"] = _ID_STRATEGY.generate(CODE, name, lat, lon)
        if row["ID"] in seen_ids:
            raise RuntimeError(
                f"{source_path}:{line_no}: duplicate generated ID={row['ID']}"
            )
        seen_ids.add(row["ID"])

        RowSupport.append_labeled_note(row, "原データ電話番号", source["Telephone number"])
        RowSupport.append_labeled_note(row, "原データ設備詳細", detail)

        rows.append(row)

    return dest, schema, rows



def main() -> None:
    dest, schema, rows = prepare()
    print(f"preflight OK: {CODE} {NAME} rows={len(rows)}")
    _WRITER.write(dest, schema, rows)
    print(f"OK {CODE} {NAME}: rows={len(rows)} source={SOURCE_FILE}")


if __name__ == "__main__":
    main()
