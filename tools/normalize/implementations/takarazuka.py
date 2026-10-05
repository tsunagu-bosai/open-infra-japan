#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

from tools.normalize.core.normalization import (
    LenientHmsTimeStrategy,
    RowSupport,
    StandardCsvWriter,
)
from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.xlsx import read_xlsx_values


ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"
RAW_DIR = ROOT / "data/raw/28-兵庫県/28214-宝塚市/public-toilet"
DEST = (
    ROOT
    / "data/normalized/28-兵庫県/28214-宝塚市/public-toilet/public-toilet.csv"
)

TARGETS = {"28214": "宝塚市"}

SOURCES = (
    {
        "namespace": "public",
        "label": "クリーンセンター管理課",
        "file": "kousyubenjo_takarazuka.xlsx",
    },
    {
        "namespace": "park",
        "label": "公園河川課",
        "file": "toire-kouen_2.xlsx",
    },
)

LEGACY_HEADER = (
    "都道府県コード又は市区町村コード",
    "NO",
    "都道府県名",
    "市区町村名",
    "名称",
    "名称_カナ",
    "名称_英語",
    "住所",
    "方書",
    "設置位置",
    "緯度",
    "経度",
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
    "多機能トイレ数",
    "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無",
    "利用開始時間",
    "利用終了時間",
    "利用可能時間特記事項",
    "画像",
    "画像_ライセンス",
    "備考",
)

LEGACY_MAP = {
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
    "利用可能時間特記事項": "利用可能時間特記事項",
    "画像": "画像",
    "画像_ライセンス": "画像_ライセンス",
    "備考": "備考",
}


def _cell_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()



TIME_NORMALIZER = LenientHmsTimeStrategy()


def read_source(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    raw_rows = read_xlsx_values(path)
    if not raw_rows:
        raise RuntimeError(f"empty XLSX: {path}")

    header = [_cell_text(value) for value in raw_rows[0]]
    while header and not header[-1]:
        header.pop()

    if tuple(header) != LEGACY_HEADER:
        raise RuntimeError(
            f"{path.name}: header drift: columns={len(header)} "
            f"expected={len(LEGACY_HEADER)}"
        )

    rows: list[dict[str, str]] = []
    for line_no, raw in enumerate(raw_rows[1:], start=2):
        values = [_cell_text(value) for value in raw[: len(header)]]
        if not any(values):
            continue
        if len(values) != len(header):
            raise RuntimeError(
                f"{path.name}:{line_no}: columns={len(values)} "
                f"expected={len(header)}"
            )
        rows.append(dict(zip(header, values)))

    return header, rows


def prepare_source(
    schema: list[str],
    source: dict[str, object],
) -> list[dict[str, str]]:
    path = RAW_DIR / str(source["file"])
    if not path.exists():
        raise RuntimeError(f"missing source: {path}")

    _, rows = read_source(path)
    if not rows:
        raise RuntimeError(f"{path.name}: no data rows")

    namespace = str(source["namespace"])
    source_label = str(source["label"])
    out: list[dict[str, str]] = []

    for line_no, src in enumerate(rows, start=2):
        source_code = src["都道府県コード又は市区町村コード"]
        if source_code != "282146":
            raise RuntimeError(
                f"{path.name}:{line_no}: unexpected municipality code "
                f"{source_code!r}"
            )

        source_no = src["NO"]
        if not source_no:
            raise RuntimeError(f"{path.name}:{line_no}: blank source NO")

        row = {field: "" for field in schema}
        row["全国地方公共団体コード"] = "282146"
        row["所在地_全国地方公共団体コード"] = "282146"
        row["ID"] = f"28214-{namespace}-{source_no}"
        row["地方公共団体名"] = "宝塚市"

        for source_field, standard_field in LEGACY_MAP.items():
            row[standard_field] = src[source_field]

        row["所在地_都道府県"] = src["都道府県名"]
        row["所在地_市区町村"] = src["市区町村名"]
        row["利用開始時間"] = TIME_NORMALIZER(src["利用開始時間"])
        row["利用終了時間"] = TIME_NORMALIZER(src["利用終了時間"])

        RowSupport.append_note(row, f"原データNO={source_no}")

        multi = src["多機能トイレ数"]
        if multi:
            RowSupport.append_note(row, f"原データ多機能トイレ数={multi}")

        RowSupport.append_note(row, f"出典区分={source_label}")
        out.append(row)

    return out



def main() -> None:
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    all_rows: list[dict[str, str]] = []
    for source in SOURCES:
        all_rows.extend(prepare_source(schema, source))

    if not all_rows:
        raise RuntimeError("no normalized rows")

    ids = [row["ID"] for row in all_rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate normalized IDs")

    names = [row["名称"] for row in all_rows]
    if len(names) != len(set(names)):
        raise RuntimeError("duplicate facility names")

    if DEST.exists():
        raise RuntimeError(f"normalized already exists: {DEST}")
    StandardCsvWriter().write(DEST, schema, all_rows)
    print(
        "OK 28214 宝塚市: "
        f"rows={len(all_rows)} sources={len(SOURCES)} "
        "id_namespace=source"
    )


if __name__ == "__main__":
    main()
