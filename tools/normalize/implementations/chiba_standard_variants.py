#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from tools.normalize.core.encoding import detect_text_encoding
from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.xlsx import read_xlsx_values
from tools.normalize.core.normalization import RowSupport, StandardCsvWriter
from tools import normalize_public_toilet as common


ROOT = Path.cwd()
RAW = ROOT / "data/raw/12-千葉県"
OUT = ROOT / "data/normalized/12-千葉県"
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "12202-銚子市",
    "12205-館山市",
    "12211-成田市",
    "12347-多古町",
}

CONFIG = {
    "12202-銚子市": {
        "file": "MM0100000008_public_toilet.csv",
        "kind": "choshi",
        "code6": "122025",
        "name": "銚子市",
    },
    "12205-館山市": {
        "file": "public_toilet.xlsx",
        "kind": "tateyama",
        "code6": "122050",
        "name": "館山市",
    },
    "12211-成田市": {
        "file": "public_toilet.csv",
        "kind": "narita",
        "code6": "122114",
        "name": "成田市",
    },
    "12347-多古町": {
        "file": "public_toilet.csv",
        "kind": "tako",
        "code6": "123471",
        "name": "多古町",
    },
}

CHOSHI_HEADER = [
    "全国地方公共団体コード", "ID", "地方公共団体名", "名称", "名称_カナ",
    "所在地_全国地方公共団体コード", "所在地_連結表記", "所在地_都道府県",
    "所在地_市区町村", "所在地_町字", "所在地_番地以下", "建物名等(方書)",
    "設置位置", "緯度", "経度", "男性トイレ総数", "男性トイレ数（小便器）",
    "男性トイレ数（和式）", "男性トイレ数（洋式）", "女性トイレ総数",
    "女性トイレ数（和式）", "女性トイレ数（洋式）", "男女共用トイレ総数",
    "男女共用トイレ数（和式）", "男女共用トイレ数（洋式）",
    "バリアフリートイレ数", "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無", "オストメイト設置トイレ有無",
    "利用可能時間特記事項",
]

TATEYAMA_HEADER = [
    "都道府県コード又は市区町村コード", "NO", "都道府県名",
    "市区町村名", "名称", "名称_カナ", "名称_英語",
    "住所", "方書", "設置位置", "緯度", "経度",
    "男性トイレ総数", "男性トイレ数（小便器）",
    "男性トイレ数（和式）", "男性トイレ数（洋式）",
    "女性トイレ総数", "女性トイレ数（和式）",
    "女性トイレ数（洋式）", "男女共用トイレ総数",
    "男女共用トイレ数（和式）",
    "男女共用トイレ数（洋式）",
    "多機能トイレ数", "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無", "利用開始時間", "利用終了時間",
    "利用可能時間特記事項",
    "画像", "画像_ライセンス", "備考",
]

NARITA_HEADER = [
    "都道府県コード又は市区町村コード", "NO", "都道府県名", "市区町村名",
    "名称（必須）", "名称_カナ（必須）", "名称_英語", "住所（必須）", "方書",
    "設置位置（必須）", "緯度", "経度", "男性トイレ総数",
    "男性トイレ数（小便器）", "男性トイレ数（和式）", "男性トイレ数（洋式）",
    "女性トイレ総数", "女性トイレ数（和式）", "女性トイレ数（洋式）",
    "男女共用トイレ総数", "男女共用トイレ数（和式）",
    "男女共用トイレ数（洋式）", "多機能トイレ数（必須）",
    "車椅子使用者用トイレ有無（必須）", "乳幼児用設備設置トイレ有無（必須）",
    "オストメイト設置トイレ有無（必須）", "利用開始時間", "利用終了時間",
    "利用可能時間特記事項", "画像", "画像_ライセンス", "備考",
]

TAKO_HEADER = [
    "都道府県コード又は市区町村コード", "都道府県名", "市区町村名",
    "名称", "名称_カナ", "住所", "設置位置", "緯度", "経度",
    "男性トイレ総数", "男性トイレ数（小便器）", "男性トイレ数（和式）",
    "男性トイレ数（洋式）", "女性トイレ総数", "女性トイレ数（和式）",
    "女性トイレ数（洋式）", "男女共用トイレ総数",
    "男女共用トイレ数（和式）", "男女共用トイレ数（洋式）",
    "多機能トイレ数", "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無", "オストメイト設置トイレ有無",
    "利用開始時間", "利用終了時間", "利用可能時間特記事項",
    "画像", "画像_ライセンス", "備考",
]

ALIASES = {
    "tateyama": {
        "NO": "ID",
        "名称": "名称",
        "名称_カナ": "名称_カナ",
        "名称_英語": "名称_英語",
        "住所": "所在地_連結表記",
        "方書": "建物名等(方書)",
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
        "画像": "画像",
        "画像_ライセンス": "画像_ライセンス",
        "備考": "備考",
    },
    "narita": {
        "NO": "ID",
        "名称（必須）": "名称",
        "名称_カナ（必須）": "名称_カナ",
        "名称_英語": "名称_英語",
        "住所（必須）": "所在地_連結表記",
        "方書": "建物名等(方書)",
        "設置位置（必須）": "設置位置",
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
        "車椅子使用者用トイレ有無（必須）": "車椅子使用者用トイレ有無",
        "乳幼児用設備設置トイレ有無（必須）": "乳幼児用設備設置トイレ有無",
        "オストメイト設置トイレ有無（必須）": "オストメイト設置トイレ有無",
        "利用開始時間": "利用開始時間",
        "利用終了時間": "利用終了時間",
        "利用可能時間特記事項": "利用可能時間特記事項",
        "画像": "画像",
        "画像_ライセンス": "画像_ライセンス",
        "備考": "備考",
    },
    "tako": {
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
        "画像": "画像",
        "画像_ライセンス": "画像_ライセンス",
        "備考": "備考",
    },
}

HEADERS = {
    "choshi": CHOSHI_HEADER,
    "tateyama": TATEYAMA_HEADER,
    "narita": NARITA_HEADER,
    "tako": TAKO_HEADER,
}


def read_source(path: Path) -> tuple[list[str], list[list[str]], str]:
    if path.suffix.lower() == ".xlsx":
        values = read_xlsx_values(path)
        if not values:
            raise RuntimeError(f"empty XLSX: {path}")
        header = [RowSupport.clean(v) for v in values[0]]
        rows = [[RowSupport.clean(v) for v in row] for row in values[1:]]
        return header, rows, "xlsx"

    encoding = detect_text_encoding(path)
    with path.open(encoding=encoding, newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            raise RuntimeError(f"empty CSV: {path}")
        rows = list(reader)
    return [RowSupport.clean(v) for v in header], [[RowSupport.clean(v) for v in row] for row in rows], encoding


def validate_code(raw_code: str, code5: str, code6: str, target: str) -> None:
    raw_code = RowSupport.clean(raw_code)
    if not raw_code:
        return
    normalized = raw_code.replace(",", "").zfill(6)
    if normalized != code6:
        raise RuntimeError(
            f"{target}: municipality code mismatch: "
            f"raw={raw_code!r} expected={code6!r}"
        )
    if normalized[:5] != code5:
        raise RuntimeError(
            f"{target}: municipality code prefix mismatch: {normalized!r}"
        )


def prepare_choshi(
    target: str,
    cfg: dict[str, Any],
    schema: list[str],
    header: list[str],
    rows: list[list[str]],
) -> list[dict[str, str]]:
    if header != CHOSHI_HEADER:
        raise RuntimeError(f"{target}: unexpected header: {header!r}")

    out_rows = []
    for line_no, values in enumerate(rows, 2):
        if not any(RowSupport.clean(v) for v in values):
            continue
        if len(values) != len(header):
            raise RuntimeError(f"{target}:{line_no}: column count mismatch")

        src = dict(zip(header, values))
        validate_code(src["全国地方公共団体コード"], target[:5], cfg["code6"], target)
        validate_code(src["所在地_全国地方公共団体コード"], target[:5], cfg["code6"], target)

        row = {field: "" for field in schema}
        for field in CHOSHI_HEADER:
            if field in row:
                row[field] = RowSupport.clean(src[field])
        out_rows.append(row)

    return out_rows


def prepare_legacy_variant(
    target: str,
    cfg: dict[str, Any],
    schema: list[str],
    header: list[str],
    rows: list[list[str]],
) -> list[dict[str, str]]:
    kind = cfg["kind"]
    expected_header = HEADERS[kind]
    if header != expected_header:
        raise RuntimeError(f"{target}: unexpected header: {header!r}")

    aliases = ALIASES[kind]
    code5 = target[:5]
    out_rows = []

    for line_no, values in enumerate(rows, 2):
        if not any(RowSupport.clean(v) for v in values):
            continue
        if len(values) != len(header):
            raise RuntimeError(f"{target}:{line_no}: column count mismatch")

        src = dict(zip(header, values))

        if kind == "narita" and not (src.get("名称（必須）") or "").strip():
            continue

        row = {field: "" for field in schema}

        for source, destination in aliases.items():
            row[destination] = RowSupport.clean(src.get(source))

        raw_code = RowSupport.clean(src.get("都道府県コード又は市区町村コード"))
        validate_code(raw_code, code5, cfg["code6"], target)

        row["全国地方公共団体コード"] = cfg["code6"]
        row["所在地_全国地方公共団体コード"] = cfg["code6"]
        row["地方公共団体名"] = cfg["name"]
        row["所在地_都道府県"] = "千葉県"
        row["所在地_市区町村"] = cfg["name"]

        if kind == "tateyama":
            multi = RowSupport.clean(src.get("多機能トイレ数"))
        elif kind == "narita":
            multi = RowSupport.clean(src.get("多機能トイレ数（必須）"))
        else:
            multi = RowSupport.clean(src.get("多機能トイレ数"))

        if multi:
            RowSupport.append_note(row, f"原データ多機能トイレ数={multi}")

        out_rows.append(row)

    return out_rows


def main() -> None:
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    prepared = []

    for target in sorted(TARGETS):
        cfg = CONFIG[target]
        source = RAW / target / "public-toilet" / cfg["file"]
        output = OUT / target / "public-toilet/public-toilet.csv"

        if not source.exists():
            raise RuntimeError(f"{target}: missing source: {source}")
        if output.exists():
            raise RuntimeError(f"{target}: normalized already exists: {output}")

        header, source_rows, source_format = read_source(source)

        if cfg["kind"] == "choshi":
            rows = prepare_choshi(target, cfg, schema, header, source_rows)
        else:
            rows = prepare_legacy_variant(target, cfg, schema, header, source_rows)

        if not rows:
            raise RuntimeError(f"{target}: no active source rows")

        patches = common.load_patches("12-千葉県", target)
        applied, problems = common.apply_patches(rows, patches, source)
        if problems:
            raise RuntimeError("\n".join(problems))

        ids = [row["ID"] for row in rows if row["ID"]]
        if len(ids) != len(set(ids)):
            raise RuntimeError(f"{target}: duplicate nonblank IDs")

        prepared.append(
            (target, cfg, output, rows, source_format, applied)
        )

    print(f"preflight OK: {len(prepared)} municipalities")
    for target, cfg, output, rows, source_format, applied in prepared:
        StandardCsvWriter().write(output, schema, rows)
        print(
            f"OK {target}: rows={len(rows)} "
            f"source={cfg['file']} format={source_format} "
            f"patches={applied}"
        )


if __name__ == "__main__":
    main()
