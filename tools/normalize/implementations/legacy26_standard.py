#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

from tools.normalize.core.encoding import detect_text_encoding
from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.normalization import (
    LenientTwentyFourTimeStrategy,
    RowSupport,
    Sha256StableIdStrategy,
    StandardCsvWriter,
)
from tools.normalize.core.schema import read_schema_fields

ROOT = Path.cwd()
RAW = ROOT / "data/raw"
OUT = ROOT / "data/normalized"
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "01211": {
        "name": "網走市",
        "prefecture": "北海道",
        "pref_dir": "01-北海道",
        "municipality_dir": "01211-網走市",
        "source": "01211_public-toilet.csv",
    },
}

EXPECTED_HEADER = [
    "都道府県コード又は市区町村コード", "都道府県名", "市区町村名", "名称", "名称_カナ",
    "住所", "設置位置", "緯度", "経度", "男性トイレ総数", "男性トイレ数（小便器）",
    "男性トイレ数（和式）", "男性トイレ数（洋式）", "女性トイレ総数", "女性トイレ数（和式）",
    "女性トイレ数（洋式）", "男女共用トイレ総数", "男女共用トイレ数（和式）",
    "男女共用トイレ数（洋式）", "多機能トイレ数", "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無", "オストメイト設置トイレ有無", "利用開始時間",
    "利用終了時間", "利用可能時間特記事項", "",
]

DIRECT_MAP = {
    "名称": "名称",
    "名称_カナ": "名称_カナ",
    "住所": "所在地_連結表記",
    "設置位置": "設置位置",
    "緯度": "緯度",
    "経度": "経度",
    "男性トイレ総数": "男性トイレ総数",
    "男性トイレ数（小便器）": "男性トイレ数（小便器）",
    "男性トイレ数（和式）": "男性トイレ数（和式）",
    "男性トイレ数（洋式）": "男性トイレ数（洋式）",
    "女性トイレ総数": "女性トイレ総数",
    "女性トイレ数（和式）": "女性トイレ数（和式）",
    "女性トイレ数（洋式）": "女性トイレ数（洋式）",
    "男女共用トイレ総数": "男女共用トイレ総数",
    "男女共用トイレ数（和式）": "男女共用トイレ数（和式）",
    "男女共用トイレ数（洋式）": "男女共用トイレ数（洋式）",
    "車椅子使用者用トイレ有無": "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無": "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無": "オストメイト設置トイレ有無",
    "利用開始時間": "利用開始時間",
    "利用終了時間": "利用終了時間",
    "利用可能時間特記事項": "利用可能時間特記事項",
}


_ID_STRATEGY = Sha256StableIdStrategy()
_WRITER = StandardCsvWriter()
_TIME_STRATEGY = LenientTwentyFourTimeStrategy()


def read_source(path: Path) -> tuple[list[str], list[list[str]], str]:
    encoding = detect_text_encoding(path)
    with path.open("r", encoding=encoding, newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            raise RuntimeError(f"{path}: empty CSV")
        rows = list(reader)
    return [RowSupport.clean(v) for v in header], rows, encoding


def prepare_one(code: str, cfg: dict[str, object], schema: list[str]) -> tuple[Path, Path, str, list[dict[str, str]]]:
    source = RAW / str(cfg["pref_dir"]) / str(cfg["municipality_dir"]) / "public-toilet" / str(cfg["source"])
    dest = OUT / str(cfg["pref_dir"]) / str(cfg["municipality_dir"]) / "public-toilet" / "public-toilet.csv"

    if not source.exists():
        raise RuntimeError(f"{code}: missing source: {source}")
    if dest.exists():
        raise RuntimeError(f"{code}: normalized already exists: {dest}")

    header, source_rows, encoding = read_source(source)
    if header != EXPECTED_HEADER:
        raise RuntimeError(f"{code}: unexpected header: {header!r}")

    expected_code6 = six_digit_municipality_code(code)
    normalized: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    for line_no, values in enumerate(source_rows, 2):
        if not any(RowSupport.clean(v) for v in values):
            continue
        if len(values) != len(EXPECTED_HEADER):
            raise RuntimeError(f"{code}:{line_no}: columns={len(values)} expected={len(EXPECTED_HEADER)}")
        if RowSupport.clean(values[-1]):
            raise RuntimeError(f"{code}:{line_no}: expected trailing empty column, got={values[-1]!r}")

        src = {name: RowSupport.clean(values[i]) for i, name in enumerate(EXPECTED_HEADER[:-1])}

        raw_code = RowSupport.clean(src["都道府県コード又は市区町村コード"])
        if raw_code.zfill(6) != expected_code6:
            raise RuntimeError(f"{code}:{line_no}: municipality code {raw_code!r} != {expected_code6!r}")
        if src["都道府県名"] != str(cfg["prefecture"]):
            raise RuntimeError(f"{code}:{line_no}: prefecture {src['都道府県名']!r} != {cfg['prefecture']!r}")
        if src["市区町村名"] != str(cfg["name"]):
            raise RuntimeError(f"{code}:{line_no}: municipality {src['市区町村名']!r} != {cfg['name']!r}")
        if not src["名称"]:
            raise RuntimeError(f"{code}:{line_no}: blank 名称")

        row = {field: "" for field in schema}
        row["全国地方公共団体コード"] = expected_code6
        row["所在地_全国地方公共団体コード"] = expected_code6
        row["地方公共団体名"] = str(cfg["name"])
        row["所在地_都道府県"] = str(cfg["prefecture"])
        row["所在地_市区町村"] = str(cfg["name"])

        for source_field, target_field in DIRECT_MAP.items():
            row[target_field] = src[source_field]

        row["利用開始時間"] = _TIME_STRATEGY(row["利用開始時間"])
        row["利用終了時間"] = _TIME_STRATEGY(row["利用終了時間"])

        ident = _ID_STRATEGY.generate(code, row["名称"], row["所在地_連結表記"], row["設置位置"], row["緯度"], row["経度"])
        if ident in seen_ids:
            raise RuntimeError(f"{code}:{line_no}: generated duplicate ID: {ident}")
        seen_ids.add(ident)
        row["ID"] = ident

        RowSupport.append_note(row, "原データにID項目なし。自治体コード・名称・住所・設置位置・緯度・経度から決定的IDを生成")
        multi = RowSupport.clean(src.get("多機能トイレ数"))
        if multi:
            RowSupport.append_note(row, f"原データ多機能トイレ数={multi}")

        normalized.append(row)

    if not normalized:
        raise RuntimeError(f"{code}: no data rows")

    return source, dest, encoding, normalized



def main() -> None:
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    prepared = []
    for code, cfg in TARGETS.items():
        source, dest, encoding, rows = prepare_one(code, cfg, schema)
        prepared.append((code, cfg, source, dest, encoding, rows))

    print(f"preflight OK: {len(prepared)} municipalities")

    for code, cfg, source, dest, encoding, rows in prepared:
        _WRITER.write(dest, schema, rows)
        print(f"OK {code} {cfg['name']}: rows={len(rows)} source={source.name} encoding={encoding}")


if __name__ == "__main__":
    main()
