#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.normalization import RowSupport, StandardCsvWriter
from tools.normalize.core.encoding import detect_text_encoding

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "13224": {
        "pref": "13-東京都",
        "mun": "13224-多摩市",
        "file": "13224_public-toilet.csv",
        "name": "多摩市",
        "mode": "legacy32",
        "code_field": "市区町村コード",
        "preserve": ["多機能トイレ数"],
        "extra_preserve": [],
        "drop_exact": [],
    },
    "23221": {
        "pref": "23-愛知県",
        "mun": "23221-新城市",
        "file": "23221_public-toilet.csv",
        "name": "新城市",
        "mode": "legacy32",
        "code_field": "都道府県コード又は市区町村コード",
        "preserve": ["多機能トイレ数"],
        "extra_preserve": [],
        "drop_exact": [],
    },
    "24212": {
        "pref": "24-三重県",
        "mun": "24212-熊野市",
        "file": "24212_public-toilet.csv",
        "name": "熊野市",
        "mode": "kumano",
        "code_field": "都道府県コード又は市区町村コード",
        "preserve": ["多機能トイレ数"],
        "extra_preserve": [],
        "drop_exact": ["6桁"],
    },
    "40203": {
        "pref": "40-福岡県",
        "mun": "40203-久留米市",
        "file": "40203_public-toilet.csv",
        "name": "久留米市",
        "mode": "legacy32",
        "code_field": "都道府県コード又は市区町村コード",
        "preserve": ["多機能トイレ数"],
        "extra_preserve": [],
        "drop_exact": [],
    },
    "41204": {
        "pref": "41-佐賀県",
        "mun": "41204-多久市",
        "file": "41204_public-toilet.csv",
        "name": "多久市",
        "mode": "taku",
        "code_field": "都道府県コード又は市区町村コード",
        "preserve": ["多機能トイレ数"],
        "extra_preserve": ["男性トイレ数（大便器）"],
        "drop_exact": [],
    },
}

LEGACY_MAP = {
    "NO": "ID",
    "都道府県名": "所在地_都道府県",
    "市区町村名": "所在地_市区町村",
    "住所": "所在地_連結表記",
    "方書": "建物名等(方書)",
}



def read_positional(path: Path):
    enc = detect_text_encoding(path)
    with path.open("r", encoding=enc, newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        raise RuntimeError(f"empty: {path}")
    return enc, rows[0], rows[1:]


def prepare_one(code, cfg, schema):
    src = ROOT / "data/raw" / cfg["pref"] / cfg["mun"] / "public-toilet" / cfg["file"]
    dest = ROOT / "data/normalized" / cfg["pref"] / cfg["mun"] / "public-toilet/public-toilet.csv"

    if not src.exists():
        raise RuntimeError(f"{code}: raw missing: {src}")
    if dest.exists():
        raise RuntimeError(f"{code}: normalized already exists: {dest}")

    enc, header, physical_rows = read_positional(src)

    # Any blank-header columns must be completely empty. This safely handles
    # Tama's 11 blank spreadsheet columns, Shinshiro's 992, and Kurume's 1.
    for i, h in enumerate(header):
        if h == "":
            for line_no, r in enumerate(physical_rows, 2):
                v = r[i].strip() if i < len(r) else ""
                if v:
                    raise RuntimeError(
                        f"{code}:{line_no}: blank-header column {i} contains {v!r}"
                    )

    # Build positional header indexes because Kumano has duplicate "6桁".
    indexes = {}
    for i, h in enumerate(header):
        if h:
            indexes.setdefault(h, []).append(i)

    def get(row, field):
        idxs = indexes.get(field, [])
        if not idxs:
            return ""
        if len(idxs) != 1:
            raise RuntimeError(f"{code}: field {field!r} occurs {len(idxs)} times")
        i = idxs[0]
        return (row[i] if i < len(row) else "").strip()

    # Kumano's duplicate 6桁 columns must exactly duplicate lat/lon.
    if cfg["mode"] == "kumano":
        six = indexes.get("6桁", [])
        if len(six) != 2:
            raise RuntimeError(f"{code}: expected two 6桁 columns, got {six!r}")
        lat_i = indexes["緯度"][0]
        lon_i = indexes["経度"][0]
        for line_no, r in enumerate(physical_rows, 2):
            vals = [(r[i] if i < len(r) else "").strip() for i in six]
            lat = (r[lat_i] if lat_i < len(r) else "").strip()
            lon = (r[lon_i] if lon_i < len(r) else "").strip()
            if vals != [lat, lon]:
                raise RuntimeError(
                    f"{code}:{line_no}: 6桁 columns do not duplicate lat/lon: "
                    f"{vals!r} vs {[lat, lon]!r}"
                )

    rows = []
    for line_no, srcrow in enumerate(physical_rows, 2):
        # Skip physically present but completely blank spreadsheet rows.
        if not any((v or "").strip() for v in srcrow):
            continue

        row = {c: "" for c in schema}

        # Copy canonical columns that exist exactly once.
        for c in schema:
            idxs = indexes.get(c, [])
            if len(idxs) == 1:
                i = idxs[0]
                row[c] = (srcrow[i] if i < len(srcrow) else "").strip()
            elif len(idxs) > 1:
                raise RuntimeError(f"{code}: canonical column duplicated: {c!r}")

        # Legacy aliases.
        code_value = get(srcrow, cfg["code_field"])
        row["全国地方公共団体コード"] = code_value
        row["地方公共団体名"] = cfg["name"]

        for old, new in LEGACY_MAP.items():
            if old in indexes:
                row[new] = get(srcrow, old)

        # Do not invent location municipality code; source only provides a
        # dataset-level municipality code in these legacy layouts.

        for field in cfg["preserve"]:
            if field in indexes:
                value = get(srcrow, field)
                if value:
                    RowSupport.append_note(row, f"原データ{field}={value}")

        for field in cfg["extra_preserve"]:
            value = get(srcrow, field)
            if value:
                RowSupport.append_note(row, f"原データ{field}={value}")

        rows.append(row)

    # Basic identity preflight.
    ids = [r["ID"] for r in rows if r["ID"]]
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"{code}: duplicate nonblank IDs after mapping")

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
        print(f"OK {code} {cfg['name']}: rows={len(rows)} encoding={enc}")


if __name__ == "__main__":
    main()
