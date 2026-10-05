#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.schema import read_schema_fields
from tools import normalize_public_toilet as common
from tools.normalize.core.normalization import (
    CsvDictSourceReader,
    RowSupport,
    Sha256StableIdStrategy,
    StandardCsvWriter,
    XlsxSourceReader,
)

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "07201": {
        "pref": "07-福島県",
        "mun": "07201-福島市",
        "name": "福島市",
        "source": "07201_public-toilet.csv",
        "headers": [
            "施設名", "設置場所", "郵便番号", "住所", "緯度", "経度",
            "電話番号", "利用可能時間", "温水", "備考",
        ],
        "map": {
            "施設名": "名称",
            "設置場所": "設置位置",
            "住所": "所在地_連結表記",
            "緯度": "緯度",
            "経度": "経度",
            "備考": "備考",
        },
        "time_note": "利用可能時間",
        "preserve": ["郵便番号", "電話番号", "温水"],
    },
    "07203": {
        "pref": "07-福島県",
        "mun": "07203-郡山市",
        "name": "郡山市",
        "source": "07203_public-toilet.csv",
        "headers": [
            "施設名", "設置場所", "郵便番号", "住所", "緯度", "経度",
            "電話番号", "利用可能時間", "備考",
        ],
        "map": {
            "施設名": "名称",
            "設置場所": "設置位置",
            "住所": "所在地_連結表記",
            "緯度": "緯度",
            "経度": "経度",
            "備考": "備考",
        },
        "time_note": "利用可能時間",
        "preserve": ["郵便番号", "電話番号"],
    },
    "09204": {
        "pref": "09-栃木県",
        "mun": "09204-佐野市",
        "name": "佐野市",
        "source": "09204_public-toilet.csv",
        "headers": ["名称", "所在地", "トイレの形式", "経度", "緯度"],
        "map": {
            "名称": "名称",
            "所在地": "所在地_連結表記",
            "緯度": "緯度",
            "経度": "経度",
        },
        "preserve": ["トイレの形式"],
    },
    "12207": {
        "pref": "12-千葉県",
        "mun": "12207-松戸市",
        "name": "松戸市",
        "location_prefecture": "千葉県",
        "location_municipality": "松戸市",
        "source": "public_toilet.csv",
        "headers": [
            "UserID", "CoodinateSystemNo", "X", "Y", "HasAttribute",
            "名称", "所在地", "男・女", "障がい者", "和・洋",
            "照明有無", "水道有無", "備考",
        ],
        "map": {
            "UserID": "ID",
            "名称": "名称",
            "所在地": "所在地_連結表記",
            "備考": "備考",
        },
        "preserve": [
            "CoodinateSystemNo",
            "X",
            "Y",
            "HasAttribute",
            "男・女",
            "障がい者",
            "和・洋",
            "照明有無",
            "水道有無",
        ],
    },
    "14208": {
        "pref": "14-神奈川県",
        "mun": "14208-逗子市",
        "name": "逗子市",
        "location_prefecture": "神奈川県",
        "location_municipality": "逗子市",
        "source": "public_toilet.csv",
        "headers": ["名称", "郵便番号", "住所", "緯度", "経度", "種別"],
        "map": {
            "名称": "名称",
            "住所": "所在地_連結表記",
            "緯度": "緯度",
            "経度": "経度",
        },
        "preserve": ["郵便番号", "種別"],
        "generate_stable_id": True,
    },
    "39205": {
        "pref": "39-高知県",
        "mun": "39205-土佐市",
        "name": "土佐市",
        "source": "202103_06.csv",
        "headers": [
            "都道府県コード又は市区町村コード",
            "NO",
            "都道府県名",
            "市区町村名",
            "名称",
            "住所",
            "備考",
        ],
        "map": {
            "NO": "ID",
            "名称": "名称",
            "住所": "所在地_連結表記",
            "都道府県名": "所在地_都道府県",
            "市区町村名": "所在地_市区町村",
            "備考": "備考",
        },
        "expected_values": {
            "都道府県コード又は市区町村コード": "392057",
            "都道府県名": "高知県",
            "市区町村名": "土佐市",
        },
        "preserve": [],
    },
    "43403": {
        "pref": "43-熊本県",
        "mun": "43403-大津町",
        "name": "大津町",
        "source": "43403_public-toilet.xlsx",
        "sheet": "大津町公衆(公園)トイレ一覧",
        "headers": ["公園名", "場所", "住所", "設備内容", "公園種別", "北緯", "東経"],
        "map": {
            "公園名": "名称",
            "場所": "設置位置",
            "住所": "所在地_連結表記",
            "北緯": "緯度",
            "東経": "経度",
        },
        "preserve": ["設備内容", "公園種別"],
    },
    "46201": {
        "pref": "46-鹿児島県",
        "mun": "46201-鹿児島市",
        "name": "鹿児島市",
        "source": "46201_public-toilet.csv",
        "headers": ["施設名", "住所", "設置基数", "設置場所", "備考"],
        "map": {
            "施設名": "名称",
            "住所": "所在地_連結表記",
            "設置場所": "設置位置",
            "備考": "備考",
        },
        "preserve": ["設置基数"],
    },
}



STABLE_ID = Sha256StableIdStrategy()
WRITER = StandardCsvWriter()


def read_source(path: Path, cfg: dict):
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return CsvDictSourceReader().read(path)
    if suffix == ".xlsx":
        sheet = cfg.get("sheet")
        if not sheet:
            raise RuntimeError(f"{path.name}: XLSX target requires sheet setting")
        return XlsxSourceReader(sheet).read(path)
    raise RuntimeError(f"unsupported source type: {path}")


def prepare_one(code: str, cfg: dict, schema: list[str]):
    src = ROOT / "data/raw" / cfg["pref"] / cfg["mun"] / "public-toilet" / cfg["source"]
    dest = ROOT / "data/normalized" / cfg["pref"] / cfg["mun"] / "public-toilet/public-toilet.csv"

    if not src.exists():
        raise RuntimeError(f"{code}: raw missing: {src}")
    if dest.exists():
        raise RuntimeError(f"{code}: normalized already exists: {dest}")

    source = read_source(src, cfg)
    header = source.header
    source_rows = source.rows
    source_format = source.source_format
    expected_headers = cfg["headers"]
    if header != expected_headers:
        raise RuntimeError(
            f"{code}: unexpected headers: actual={header!r} expected={expected_headers!r}"
        )
    if not source_rows:
        raise RuntimeError(f"{code}: no data rows after blank-row filtering")

    mapping = cfg["map"]
    preserve = cfg.get("preserve", [])
    time_note = cfg.get("time_note")
    code6 = six_digit_municipality_code(code)

    for source_name, target_name in mapping.items():
        if source_name not in expected_headers:
            raise RuntimeError(f"{code}: mapped source header missing: {source_name!r}")
        if target_name not in schema:
            raise RuntimeError(f"{code}: mapped target column missing: {target_name!r}")
    for source_name in preserve:
        if source_name not in expected_headers:
            raise RuntimeError(f"{code}: preserve source header missing: {source_name!r}")
    expected_values = cfg.get("expected_values", {})

    for source_name in expected_values:
        if source_name not in expected_headers:
            raise RuntimeError(
                f"{code}: expected-value source header missing: "
                f"{source_name!r}"
            )
    if time_note and time_note not in expected_headers:
        raise RuntimeError(f"{code}: time-note source header missing: {time_note!r}")

    rows: list[dict[str, str]] = []
    for row_no, source_row in enumerate(source_rows, 2):
        for source_name, expected_value in expected_values.items():
            actual = source_row.get(source_name, "")
            if actual != expected_value:
                raise RuntimeError(
                    f"{code}:{row_no}: unexpected "
                    f"{source_name}={actual!r} "
                    f"expected={expected_value!r}"
                )

        row = {column: "" for column in schema}
        row["全国地方公共団体コード"] = code6
        row["所在地_全国地方公共団体コード"] = code6
        row["地方公共団体名"] = cfg["name"]

        if cfg.get("location_prefecture"):
            row["所在地_都道府県"] = cfg["location_prefecture"]
        if cfg.get("location_municipality"):
            row["所在地_市区町村"] = cfg["location_municipality"]

        for source_name, target_name in mapping.items():
            row[target_name] = source_row.get(source_name, "")

        if cfg.get("generate_stable_id") and not row["ID"]:
            row["ID"] = STABLE_ID.generate(
                code,
                row["名称"],
                row["所在地_連結表記"],
                row["設置位置"],
                row["緯度"],
                row["経度"],
            )

        if time_note:
            row["利用可能時間特記事項"] = source_row.get(time_note, "")

        for source_name in preserve:
            value = source_row.get(source_name, "")
            if value:
                RowSupport.append_note(row, f"原データ{source_name}={value}")

        if code == "43403":
            # 大津町の「設備内容」は設備ごとの個数を明示している。
            # 多目的トイレは明示された個数だけを標準の
            # バリアフリートイレ数へ反映し、記載がない場合は推測で0にしない。
            equipment = source_row.get("設備内容", "")
            normalized_equipment = equipment.translate(
                str.maketrans(
                    "０１２３４５６７８９（）",
                    "0123456789()",
                )
            )

            m = re.search(r"多目的\((\d+)", normalized_equipment)
            if m:
                row["バリアフリートイレ数"] = m.group(1)

            # オストメイトも個数が明示された場合だけ肯定情報として反映する。
            m = re.search(r"オストメイト\s*(\d+)", normalized_equipment)
            if m and int(m.group(1)) > 0:
                row["オストメイト設置トイレ有無"] = "有"

        rows.append(row)

    return dest, source_format, rows


def main() -> None:
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    prepared = []
    for code, cfg in TARGETS.items():
        dest, source_format, rows = prepare_one(code, cfg, schema)
        prepared.append((code, cfg, dest, source_format, rows))

    print(f"preflight OK: {len(prepared)} municipalities")

    for code, cfg, dest, source_format, rows in prepared:
        source_path = (
            ROOT / "data/raw" / cfg["pref"] / cfg["mun"]
            / "public-toilet" / cfg["source"]
        )
        patches = common.load_patches(cfg["pref"], cfg["mun"])
        applied, problems = common.apply_patches(rows, patches, source_path)
        if problems:
            raise RuntimeError("\n".join(problems))

        WRITER.write(dest, schema, rows)
        print(
            f"OK {code} {cfg['name']}: "
            f"rows={len(rows)} source={cfg['source']} format={source_format} "
            f"patches={applied}"
        )


if __name__ == "__main__":
    main()
