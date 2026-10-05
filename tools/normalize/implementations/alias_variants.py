#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.normalization import (
    CsvDictSourceReader,
    RowSupport,
    StandardCsvWriter,
)

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "11201": {
        "pref": "11-埼玉県",
        "mun": "11201-川越市",
        "file": "11201_public-toilet.csv",
        "aliases": {
            "建物名等（方書）": "建物名等(方書)",
        },
        "preserve": [],
    },
    "11211": {
        "pref": "11-埼玉県",
        "mun": "11211-本庄市",
        "file": "11211_public-toilet.csv",
        "aliases": {
            "建物名等_方書": "建物名等(方書)",
            "男性トイレ数_小便器": "男性トイレ数（小便器）",
            "男性トイレ数_和式": "男性トイレ数（和式）",
            "男性トイレ数_洋式": "男性トイレ数（洋式）",
            "女性トイレ数_和式": "女性トイレ数（和式）",
            "女性トイレ数_洋式": "女性トイレ数（洋式）",
            "男女共用トイレ数_和式": "男女共用トイレ数（和式）",
            "男女共用トイレ数_洋式": "男女共用トイレ数（洋式）",
        },
        "preserve": [],
    },
    "10421": {
        "pref": "10-群馬県",
        "mun": "10421-中之条町",
        "file": "3682.csv",
        "aliases": {
            "地方公共団体コード": "全国地方公共団体コード",
            "所在地_地方公共団体コード": "所在地_全国地方公共団体コード",
        },
        "preserve": ["多機能トイレ数"],
    },
    "13308": {
        "pref": "13-東京都",
        "mun": "13308-奥多摩町",
        "file": "133086_public_toilet.csv",
        "time_seconds_corrections": 76,
        "aliases": {
            "所在地_連結標記": "所在地_連結表記",
        },
        "preserve": [],
    },
    "17361": {
        "pref": "17-石川県",
        "mun": "17361-津幡町",
        "file": "17361_public-toilet.csv",
        "aliases": {
            "建物名等（方書）": "建物名等(方書)",
            "車椅子使用者用トイレ有無\n（プルダウンから選択）": "車椅子使用者用トイレ有無",
            "乳幼児用設備設置トイレ有無\n（プルダウンから選択）": "乳幼児用設備設置トイレ有無",
            "オストメイト設置トイレ有無\n（プルダウンから選択）": "オストメイト設置トイレ有無",
        },
        "preserve": [],
    },
    "28229": {
        "pref": "28-兵庫県",
        "mun": "28229-たつの市",
        "file": "13toilet.csv",
        "aliases": {
            "建物名等_方書": "建物名等(方書)",
            "男性トイレ数_小便器": "男性トイレ数（小便器）",
            "男性トイレ数_和式": "男性トイレ数（和式）",
            "男性トイレ数_洋式": "男性トイレ数（洋式）",
            "女性トイレ数_和式": "女性トイレ数（和式）",
            "女性トイレ数_洋式": "女性トイレ数（洋式）",
            "男女共用トイレ数_和式": "男女共用トイレ数（和式）",
            "男女共用トイレ数_洋式": "男女共用トイレ数（洋式）",
        },
        "preserve": [],
    },
    "29205": {
        "pref": "29-奈良県",
        "mun": "29205-橿原市",
        "file": "29205_public-toilet.csv",
        "aliases": {
            "女性トイレ数": "女性トイレ総数",
        },
        "preserve": [],
    },
    "37208": {
        "pref": "37-香川県",
        "mun": "37208-三豊市",
        "file": "372081_public_toilet.csv",
        "time_seconds_corrections": 78,
        "aliases": {
            "建物名等（方書）": "建物名等(方書)",
            "画像ライセンス": "画像_ライセンス",
        },
        "preserve": [],
    },
    "46221": {
        "pref": "46-鹿児島県",
        "mun": "46221-志布志市",
        "file": "46221_public-toilet.csv",
        "aliases": {
            "バリアフリートイレトイレ数": "バリアフリートイレ数",
        },
        "preserve": [],
    },
    "47211": {
        "pref": "47-沖縄県",
        "mun": "47211-沖縄市",
        "file": "47211_public-toilet.csv",
        "aliases": {
            "高度の識別": "高度の種別",
        },
        "preserve": [],
    },
}



TIME_FIELDS = ("利用開始時間", "利用終了時間")


def normalize_hhmmss(value: str) -> str:
    s = (value or "").strip()
    if not s:
        return ""

    m = re.fullmatch(r"(\d{1,2}):(\d{2}):(\d{2})", s)
    if not m:
        return s

    hh, mm, ss = map(int, m.groups())
    if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59):
        raise RuntimeError(f"invalid time: {s!r}")

    return f"{hh:02d}:{mm:02d}"


READER = CsvDictSourceReader()
WRITER = StandardCsvWriter()


def prepare_one(code, cfg, schema):
    src = ROOT / "data/raw" / cfg["pref"] / cfg["mun"] / "public-toilet" / cfg["file"]
    dest = ROOT / "data/normalized" / cfg["pref"] / cfg["mun"] / "public-toilet/public-toilet.csv"

    if not src.exists():
        raise RuntimeError(f"{code}: raw missing: {src}")
    if dest.exists():
        raise RuntimeError(f"{code}: normalized already exists: {dest}")

    source = READER.read(src)
    enc = source.source_format
    header = source.header
    if len(set(header)) != len(header):
        raise RuntimeError(f"{code}: duplicate header names found")

    rows = []
    for line_no, clean in enumerate(source.rows, 2):
        row = {c: clean.get(c, "") for c in schema}

        for old, new in cfg["aliases"].items():
            if old not in header:
                raise RuntimeError(f"{code}: alias source missing: {old!r}")
            if new in header and clean.get(new, ""):
                raise RuntimeError(
                    f"{code}:{line_no}: both alias and canonical have values: "
                    f"{old!r} -> {new!r}"
                )
            row[new] = clean.get(old, "")

        for field in cfg["preserve"]:
            if field not in header:
                raise RuntimeError(f"{code}: preserve source missing: {field!r}")
            value = clean.get(field, "")
            if value:
                RowSupport.append_note(row, f"原データ{field}={value}")

        rows.append(row)

    expected_time_corrections = cfg.get("time_seconds_corrections", 0)
    time_corrections = 0
    if expected_time_corrections:
        for row in rows:
            for field in TIME_FIELDS:
                old = row[field]
                new = normalize_hhmmss(old)
                if new != old:
                    row[field] = new
                    time_corrections += 1

        if time_corrections != expected_time_corrections:
            raise RuntimeError(
                f"{code}: expected {expected_time_corrections} time corrections, "
                f"got {time_corrections}"
            )

    if not rows:
        raise RuntimeError(f"{code}: no data rows after blank-row filtering")

    expected_noncanonical = set(cfg["aliases"]) | set(cfg["preserve"])
    actual_noncanonical = {h for h in header if h not in schema}
    if actual_noncanonical != expected_noncanonical:
        raise RuntimeError(
            f"{code}: unexpected noncanonical headers: "
            f"actual={sorted(actual_noncanonical)!r} "
            f"expected={sorted(expected_noncanonical)!r}"
        )

    missing_after_alias = [
        c for c in schema
        if c not in header and c not in set(cfg["aliases"].values())
    ]
    if missing_after_alias:
        raise RuntimeError(
            f"{code}: unmapped schema columns remain: {missing_after_alias!r}"
        )

    return src, dest, enc, rows


def main():
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    prepared = []
    for code, cfg in TARGETS.items():
        prepared.append((code, cfg, *prepare_one(code, cfg, schema)))

    print(f"preflight OK: {len(prepared)} municipalities")

    for code, cfg, src, dest, enc, rows in prepared:
        WRITER.write(dest, schema, rows)
        print(
            f"OK {code} {cfg['mun'].split('-', 1)[1]}: "
            f"rows={len(rows)} encoding={enc}"
        )


if __name__ == "__main__":
    main()
