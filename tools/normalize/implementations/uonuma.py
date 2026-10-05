from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from tools.normalize.core.linkdata_xls import LinkDataXlsReader
from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.normalization import StandardCsvWriter
from tools.normalize_public_toilet import apply_patches, load_patches


ROOT = Path.cwd()
RAW = ROOT / "data/raw"
OUT = ROOT / "data/normalized"
SCHEMA = ROOT / "schema/standard/public-toilet/schema.csv"

PREF_DIR = "15-新潟県"
MUNI_DIR = "15225-魚沼市"
SOURCE = RAW / PREF_DIR / MUNI_DIR / "public-toilet/public_toilet_.xls"
DEST = OUT / PREF_DIR / MUNI_DIR / "public-toilet/public-toilet.csv"

CODE5 = "15225"
CITY_NAME = "魚沼市"

REMOVED = {
    (
        "小沢平バイオトイレ",
        "福島県南会津郡檜枝岐村燧ケ岳",
    ),
}


def read_schema() -> list[str]:
    with SCHEMA.open("r", encoding="utf-8-sig", newline="") as f:
        return [row["name"] for row in csv.DictReader(f)]


def clean(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def stable_id(name: str, address: str, latitude: str, longitude: str) -> str:
    key = "|".join(
        (
            CODE5,
            clean(name),
            clean(address),
            clean(latitude),
            clean(longitude),
        )
    )
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12].upper()
    return f"{CODE5}-{digest}"


def normalize_bool(value: str) -> str:
    value = clean(value)

    if not value:
        return ""

    if value in {"有", "あり", "1", "○"}:
        return "有"

    if value in {"無", "なし", "0", "×"}:
        return "無"

    return value


def main() -> None:
    fields = read_schema()
    if len(fields) != 39:
        raise RuntimeError(f"schema columns={len(fields)} expected=39")

    source_rows = LinkDataXlsReader().read(SOURCE)

    rows: list[dict[str, str]] = []
    excluded = 0

    for src in source_rows:
        name = clean(src.get("#property"))
        address = clean(src.get("住所"))

        # LinkDataでは第1列のproperty名が #property 自身になる。
        # 実データ行では第1列が施設名称。
        if not name:
            continue

        if (name, address) in REMOVED:
            excluded += 1
            continue

        latitude = clean(
            src.get("http://www.w3.org/2003/01/geo/wgs84_pos#lat")
        )
        longitude = clean(
            src.get("http://www.w3.org/2003/01/geo/wgs84_pos#long")
        )

        row = {field: "" for field in fields}

        row["全国地方公共団体コード"] = six_digit_municipality_code(CODE5)
        row["ID"] = stable_id(name, address, latitude, longitude)
        row["地方公共団体名"] = CITY_NAME
        row["名称"] = name
        row["名称_カナ"] = clean(src.get("名称_カナ"))

        row["所在地_全国地方公共団体コード"] = six_digit_municipality_code(
            CODE5
        )
        row["所在地_連結表記"] = address
        row["所在地_都道府県"] = "新潟県"
        row["所在地_市区町村"] = CITY_NAME

        row["設置位置"] = clean(src.get("設置位置"))
        row["緯度"] = latitude
        row["経度"] = longitude

        for field in (
            "男性トイレ総数",
            "男性トイレ数（小便器）",
            "男性トイレ数（和式）",
            "男性トイレ数（洋式）",
            "女性トイレ総数",
            "女性トイレ数（和式）",
            "女性トイレ数（洋式）",
            "男女共用トイレ総数",
            "男女共用トイレ数（和式）",
            "男女共用トイレ数（洋式）",
        ):
            row[field] = clean(src.get(field))

        multi = clean(src.get("多機能トイレ数"))
        if multi:
            row["備考"] = f"多機能トイレ数:{multi}"

        row["車椅子使用者用トイレ有無"] = normalize_bool(
            src.get("車椅子使用者用トイレ有無")
        )
        row["乳幼児用設備設置トイレ有無"] = normalize_bool(
            src.get("乳幼児用設備設置トイレ有無")
        )
        row["オストメイト設置トイレ有無"] = normalize_bool(
            src.get("オストメイト設置トイレ有無")
        )

        row["利用可能時間特記事項"] = clean(
            src.get("利用可能時間特記事項")
        )

        rows.append(row)

    if excluded != 1:
        raise RuntimeError(
            f"{MUNI_DIR}: removed facility count={excluded} expected=1"
        )

    patches = load_patches(PREF_DIR, MUNI_DIR)
    applied, problems = apply_patches(rows, patches, SOURCE)

    if problems:
        raise RuntimeError(
            f"{MUNI_DIR}: patch適用失敗: " + " | ".join(problems)
        )

    StandardCsvWriter().write(DEST, fields, rows)

    print(
        f"OK {MUNI_DIR}: rows={len(rows)} "
        f"excluded={excluded} patches={applied}"
    )


if __name__ == "__main__":
    main()
