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

CODE = "27100"
CODE6 = "271004"
NAME = "大阪市"
PREF = "大阪府"
PREF_DIR = "27-大阪府"
MUN_DIR = "27100-大阪市"
SOURCE_FILE = "opendata_1011.csv"

EXPECTED_HEADER = [
    "施設名称",
    "所在地",
    "施設名かな",
    "カテゴリ",
    "分類",
    "TEL",
    "FAX",
    "URL",
    "URL2",
    "バリアフリー情報",
    "詳細情報",
    "備考",
    "経度",
    "緯度",
    "分類",
]


_ID_STRATEGY = Sha256StableIdStrategy(template="{code}-{digest}")
_WRITER = StandardCsvWriter()

def read_source(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise RuntimeError(f"{path}: empty CSV") from exc

        if header != EXPECTED_HEADER:
            raise RuntimeError(
                f"{path}: header mismatch\n"
                f"actual={header!r}\n"
                f"expected={EXPECTED_HEADER!r}"
            )

        rows: list[list[str]] = []
        for line_no, values in enumerate(reader, 2):
            if not any(RowSupport.clean(v) for v in values):
                continue
            if len(values) != len(EXPECTED_HEADER):
                raise RuntimeError(
                    f"{path}:{line_no}: columns={len(values)} "
                    f"expected={len(EXPECTED_HEADER)}"
                )
            rows.append([RowSupport.clean(v) for v in values])

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

    for line_no, values in enumerate(source_rows, 2):
        name = values[0]
        address = values[1]
        kana = values[2]
        category = values[3]
        classification_a = values[4]
        tel = values[5]
        fax = values[6]
        url = values[7]
        url2 = values[8]
        barrier_info = values[9]
        detail = values[10]
        source_note = values[11]
        lon = values[12]
        lat = values[13]
        classification_b = values[14]

        if category != "公衆トイレ":
            raise RuntimeError(
                f"{source_path}:{line_no}: カテゴリ={category!r}"
            )
        if classification_a != classification_b:
            raise RuntimeError(
                f"{source_path}:{line_no}: duplicated 分類 mismatch "
                f"{classification_a!r} != {classification_b!r}"
            )
        if classification_a not in {"公衆便所", "車いす対応公衆便所"}:
            raise RuntimeError(
                f"{source_path}:{line_no}: 分類={classification_a!r}"
            )
        if not name or not address or not lat or not lon:
            raise RuntimeError(
                f"{source_path}:{line_no}: required value blank "
                f"name={name!r} address={address!r} lat={lat!r} lon={lon!r}"
            )

        row = {field: "" for field in schema}
        row["全国地方公共団体コード"] = CODE6
        row["所在地_全国地方公共団体コード"] = CODE6
        row["地方公共団体名"] = NAME
        row["名称"] = name
        row["名称_カナ"] = kana
        row["所在地_連結表記"] = address
        row["所在地_都道府県"] = PREF
        row["所在地_市区町村"] = NAME
        row["緯度"] = lat
        row["経度"] = lon

        # 「車いす対応公衆便所」は明示的な肯定情報。
        # 通常の「公衆便所」は非対応を意味しないため「無」にはしない。
        if classification_a == "車いす対応公衆便所":
            row["車椅子使用者用トイレ有無"] = "有"

        row["備考"] = source_note

        row["ID"] = _ID_STRATEGY.generate(CODE, name, address, lat, lon)
        if row["ID"] in seen_ids:
            raise RuntimeError(
                f"{source_path}:{line_no}: duplicate generated ID={row['ID']}"
            )
        seen_ids.add(row["ID"])

        # 独自列は意味を変えず備考へ保持する。
        RowSupport.append_labeled_note(row, "原データカテゴリ", category)
        RowSupport.append_labeled_note(row, "原データ分類", classification_a)
        RowSupport.append_labeled_note(row, "原データTEL", tel)
        RowSupport.append_labeled_note(row, "原データFAX", fax)
        RowSupport.append_labeled_note(row, "原データURL", url)
        RowSupport.append_labeled_note(row, "原データURL2", url2)
        RowSupport.append_labeled_note(row, "原データバリアフリー情報", barrier_info)
        RowSupport.append_labeled_note(row, "原データ詳細情報", detail)

        rows.append(row)

    return dest, schema, rows



def main() -> None:
    dest, schema, rows = prepare()
    print(f"preflight OK: {CODE} {NAME} rows={len(rows)}")
    _WRITER.write(dest, schema, rows)
    print(f"OK {CODE} {NAME}: rows={len(rows)} source={SOURCE_FILE}")


if __name__ == "__main__":
    main()
