#!/usr/bin/env python3
from __future__ import annotations

import csv
from collections import defaultdict
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

SOURCE = (
    ROOT
    / "data/raw/36-徳島県/prefecture/public-toilet/"
    "利用可能なトイレ一覧表.csv"
)

OUT_ROOT = ROOT / "data/normalized/36-徳島県"

EXPECTED_HEADER = [
    "名称",
    "名称_カナ",
    "住所",
    "男性トイレの有無",
    "女性トイレの有無",
    "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無",
    "利用可能な曜日",
    "利用開始時間",
    "利用終了時間",
    "利用可能時間特記事項",
]

MUNICIPALITIES = [
    ("36201", "徳島市"),
    ("36202", "鳴門市"),
    ("36203", "小松島市"),
    ("36204", "阿南市"),
    ("36205", "吉野川市"),
    ("36206", "阿波市"),
    ("36207", "美馬市"),
    ("36208", "三好市"),
    ("36301", "勝浦町"),
    ("36302", "上勝町"),
    ("36321", "佐那河内村"),
    ("36341", "石井町"),
    ("36342", "神山町"),
    ("36368", "那賀町"),
    ("36383", "牟岐町"),
    ("36387", "美波町"),
    ("36388", "海陽町"),
    ("36401", "松茂町"),
    ("36402", "北島町"),
    ("36403", "藍住町"),
    ("36404", "板野町"),
    ("36405", "上板町"),
    ("36468", "つるぎ町"),
    ("36489", "東みよし町"),
]

# 36202 鳴門市・36387 美波町は既存の自治体別データを優先する。
EXCLUDED_CODES = {"36202", "36387"}

TARGETS = [
    (code, name)
    for code, name in MUNICIPALITIES
    if code not in EXCLUDED_CODES
]

BOOLEAN_FIELDS = (
    "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無",
)


_ID_STRATEGY = Sha256StableIdStrategy(
    digest_length=12,
    template="{code}-{digest}",
)
_WRITER = StandardCsvWriter()


def municipality_for_address(address: str) -> tuple[str, str]:
    matches = [
        (code, name)
        for code, name in MUNICIPALITIES
        if name in address
    ]

    if len(matches) != 1:
        raise RuntimeError(
            f"municipality match count={len(matches)} "
            f"address={address!r} matches={matches!r}"
        )

    return matches[0]


def main() -> None:
    if not SOURCE.exists():
        raise RuntimeError(f"missing source: {SOURCE}")

    schema = read_schema_fields(SCHEMA_PATH)

    if len(schema) != 39:
        raise RuntimeError(
            f"schema columns={len(schema)} expected=39"
        )

    with SOURCE.open(
        "r",
        encoding="cp932",
        newline="",
    ) as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        source_rows = [
            source
            for source in reader
            if RowSupport.has_meaningful_value(source.values())
        ]

    if header != EXPECTED_HEADER:
        raise RuntimeError(
            f"source header drift: {header!r}"
        )

    if not source_rows:
        raise RuntimeError("source has no data rows")

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for line_no, source in enumerate(source_rows, start=2):
        src = {
            k: RowSupport.clean(v)
            for k, v in source.items()
        }

        if not src["名称"]:
            raise RuntimeError(
                f"line {line_no}: blank 名称"
            )

        if not src["住所"]:
            raise RuntimeError(
                f"line {line_no}: blank 住所"
            )

        code5, municipality_name = municipality_for_address(
            src["住所"]
        )


        for field in (
            "男性トイレの有無",
            "女性トイレの有無",
            *BOOLEAN_FIELDS,
        ):
            if src[field] not in {"有", "無"}:
                raise RuntimeError(
                    f"line {line_no}: invalid "
                    f"{field}={src[field]!r}"
                )

        row = {
            field: ""
            for field in schema
        }

        code6 = six_digit_municipality_code(code5)

        row["全国地方公共団体コード"] = code6
        row["所在地_全国地方公共団体コード"] = code6
        row["地方公共団体名"] = municipality_name

        row["名称"] = src["名称"]
        row["名称_カナ"] = src["名称_カナ"]

        row["所在地_連結表記"] = src["住所"]
        row["所在地_都道府県"] = "徳島県"
        row["所在地_市区町村"] = municipality_name

        for field in BOOLEAN_FIELDS:
            row[field] = src[field]

        row["利用開始時間"] = src["利用開始時間"]
        row["利用終了時間"] = src["利用終了時間"]
        row["利用可能時間特記事項"] = (
            src["利用可能時間特記事項"]
        )

        row["ID"] = _ID_STRATEGY.generate(
            code5,
            src["名称"],
            src["住所"],
        )

        RowSupport.append_note(
            row,
            f"原データ男性トイレの有無={src['男性トイレの有無']}",
        )
        RowSupport.append_note(
            row,
            f"原データ女性トイレの有無={src['女性トイレの有無']}",
        )
        RowSupport.append_note(
            row,
            f"原データ利用可能な曜日={src['利用可能な曜日']}",
        )
        RowSupport.append_note(
            row,
            "原データにID項目なし。"
            "自治体コード・名称・住所から決定的IDを生成",
        )

        grouped[code5].append(row)

    generated = 0
    total_rows = 0

    for code5, municipality_name in TARGETS:
        rows = grouped[code5]

        if not rows:
            raise RuntimeError(f"{code5}: no normalized rows")

        ids = [row["ID"] for row in rows]

        if len(ids) != len(set(ids)):
            raise RuntimeError(
                f"{code5}: duplicate generated ID"
            )

        dest = (
            OUT_ROOT
            / f"{code5}-{municipality_name}"
            / "public-toilet"
            / "public-toilet.csv"
        )

        _WRITER.write(dest, schema, rows)

        generated += 1
        total_rows += len(rows)

        print(
            f"OK {code5} {municipality_name}: "
            f"rows={len(rows)}"
        )

    print(
        f"OK Tokushima prefecture dataset: "
        f"municipalities={generated} "
        f"rows={total_rows} "
        f"excluded_existing={len(EXCLUDED_CODES)}"
    )


if __name__ == "__main__":
    main()
