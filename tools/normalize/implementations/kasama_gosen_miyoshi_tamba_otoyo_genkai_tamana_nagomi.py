#!/usr/bin/env python3
from __future__ import annotations
from tools.normalize.core.normalization import RowSupport, StandardCsvWriter

import csv
from pathlib import Path
from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.encoding import detect_text_encoding

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "08216": {
        "pref": "08-茨城県",
        "mun": "08216-笠間市",
        "file": "08216_public-toilet.csv",
        "name": "笠間市",
        "aliases": {},
        "preserve": [],
    },
    "15218": {
        "pref": "15-新潟県",
        "mun": "15218-五泉市",
        "file": "152188_public_toilet20260401.csv",
        "name": "五泉市",
        "aliases": {
            "住所": "所在地_連結表記",
            "方書": "建物名等(方書)",
        },
        "preserve": ["多機能トイレ数"],
    },
    "23236": {
        "pref": "23-愛知県",
        "mun": "23236-みよし市",
        "file": "13_232360_public_toilet.csv",
        "name": "みよし市",
        "aliases": {},
        "preserve": [],
    },
    "28223": {
        "pref": "28-兵庫県",
        "mun": "28223-丹波市",
        "file": "28223_public-toilet.csv",
        "name": "丹波市",
        "aliases": {
            "市区町村コード": "全国地方公共団体コード",
            "NO": "ID",
            "都道府県名": "所在地_都道府県",
            "市区町村名": "所在地_市区町村",
            "住所": "所在地_連結表記",
            "方書": "建物名等(方書)",
        },
        "preserve": ["多機能トイレ数"],
    },
    "39344": {
        "pref": "39-高知県",
        "mun": "39344-大豊町",
        "file": "20220824.csv",
        "name": "大豊町",
        "aliases": {
            "市区町村コード": "全国地方公共団体コード",
            "NO": "ID",
            "都道府県名": "所在地_都道府県",
            "市区町村名": "所在地_市区町村",
            "住所": "所在地_連結表記",
        },
        "preserve": [],
    },
    "41387": {
        "pref": "41-佐賀県",
        "mun": "41387-玄海町",
        "file": "41387_public-toilet.csv",
        "name": "玄海町",
        "aliases": {
            "都道府県コード又は市区町村コード": "全国地方公共団体コード",
            "NO": "ID",
            "都道府県名": "所在地_都道府県",
            "市区町村名": "所在地_市区町村",
            "住所": "所在地_連結表記",
        },
        "preserve": ["多機能トイレ数"],
    },
    "43206": {
        "pref": "43-熊本県",
        "mun": "43206-玉名市",
        "file": "43206_public-toilet.csv",
        "name": "玉名市",
        "aliases": {
            "都道府県コード又は市区町村コード": "全国地方公共団体コード",
            "都道府県名": "所在地_都道府県",
            "市区町村名": "所在地_市区町村",
            "住所": "所在地_連結表記",
            "方書": "建物名等(方書)",
        },
        "preserve": ["多機能トイレ数"],
    },
    "43369": {
        "pref": "43-熊本県",
        "mun": "43369-和水町",
        "file": "43369_public-toilet.csv",
        "name": "和水町",
        "aliases": {},
        "preserve": [],
    },
}


def prepare_one(code, cfg, schema):
    src = ROOT / "data/raw" / cfg["pref"] / cfg["mun"] / "public-toilet" / cfg["file"]
    dest = ROOT / "data/normalized" / cfg["pref"] / cfg["mun"] / "public-toilet/public-toilet.csv"

    if not src.exists():
        raise RuntimeError(f"{code}: raw missing: {src}")
    if dest.exists():
        raise RuntimeError(f"{code}: normalized already exists: {dest}")

    enc = detect_text_encoding(src)

    with src.open("r", encoding=enc, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []

        if len(set(header)) != len(header):
            raise RuntimeError(f"{code}: duplicate header names found")

        aliases = cfg["aliases"]
        preserve = cfg["preserve"]

        actual_extras = {h for h in header if h not in schema}
        expected_extras = set(aliases) | set(preserve)

        if actual_extras != expected_extras:
            raise RuntimeError(
                f"{code}: unexpected extra headers: "
                f"actual={sorted(actual_extras)!r} expected={sorted(expected_extras)!r}"
            )

        rows = []
        for line_no, srcrow in enumerate(reader, 2):
            if None in srcrow:
                raise RuntimeError(
                    f"{code}:{line_no}: overflow columns={srcrow[None]!r}"
                )

            clean = {k: (v or "").strip() for k, v in srcrow.items()}
            if not any(clean.values()):
                continue

            row = {c: clean.get(c, "") for c in schema}

            for old, new in aliases.items():
                if old not in header:
                    raise RuntimeError(f"{code}: alias source missing: {old!r}")
                if new in header and clean.get(new, ""):
                    raise RuntimeError(
                        f"{code}:{line_no}: both alias and canonical have values: "
                        f"{old!r} -> {new!r}"
                    )
                row[new] = clean.get(old, "")

            for field in preserve:
                if field not in header:
                    raise RuntimeError(f"{code}: preserve field missing: {field!r}")
                if clean.get(field, ""):
                    RowSupport.append_note(row, f"原データ{field}={clean[field]}")

            if not row.get("地方公共団体名", ""):
                row["地方公共団体名"] = cfg["name"]

            # When the source has a canonical municipality code but omits the
            # location municipality code, do not invent it. Leave it blank.
            rows.append(row)


    if code == "08216":

        for row in rows:
            start = (row.get("利用開始時間") or "").strip()
            end = (row.get("利用終了時間") or "").strip()

            if start != "終日" and end != "終日":
                continue

            if start != "終日":
                raise RuntimeError(
                    f"笠間市 unexpected end-only 終日: ID={row.get('ID')!r}"
                )
            if end not in ("", "終日"):
                raise RuntimeError(
                    f"笠間市 unexpected end value: "
                    f"ID={row.get('ID')!r} end={end!r}"
                )

            RowSupport.append_note(row, "原データ利用開始時間=終日")
            row["利用開始時間"] = "00:00"

            if end == "終日":
                RowSupport.append_note(row, "原データ利用終了時間=終日")

            row["利用終了時間"] = "23:59"



    if code == "43206":

        for row in rows:
            raw_id = (row.get("ID") or "").strip()
            if raw_id != "4.32E+13":
                raise RuntimeError(
                    f"玉名市 unexpected ID: {raw_id!r} "
                    f"name={row.get('名称')!r}"
                )

            RowSupport.append_note(row, "原データID=4.32E+13")
            row["ID"] = ""

            start = (row.get("利用開始時間") or "").strip()
            if start != "0:00":
                raise RuntimeError(
                    f"玉名市 unexpected start: {start!r} "
                    f"name={row.get('名称')!r}"
                )
            row["利用開始時間"] = "00:00"

            wheelchair = (
                row.get("車椅子使用者用トイレ有無") or ""
            ).strip()

            if wheelchair in ("有(15)", "有(2)"):
                RowSupport.append_note(
                    row,
                    f"原データ車椅子使用者用トイレ有無={wheelchair}",
                )
                row["車椅子使用者用トイレ有無"] = "有"
            elif wheelchair not in ("有", "無", ""):
                raise RuntimeError(
                    "玉名市 unexpected wheelchair value: "
                    f"{wheelchair!r} name={row.get('名称')!r}"
                )


    return dest, enc, rows


def main():
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    prepared = []
    for code, cfg in TARGETS.items():
        dest, enc, rows = prepare_one(code, cfg, schema)
        prepared.append((code, cfg, dest, enc, rows))

    print(f"preflight OK: {len(prepared)} municipalities")

    for code, cfg, dest, enc, rows in prepared:
        StandardCsvWriter().write(dest, schema, rows)
        print(
            f"OK {code} {cfg['name']}: "
            f"rows={len(rows)} encoding={enc}"
        )


if __name__ == "__main__":
    main()
