#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from tools.normalize.core.normalization import RowSupport
from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.encoding import detect_text_encoding

ROOT = Path.cwd()
RAW = ROOT / "data/raw"
NORMALIZED = ROOT / "data/normalized"
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"
TARGETS = {"43505": ("43-熊本県", "43505-多良木町")}



def normalize_taragi(schema):
    raw_dir = RAW / "43-熊本県/43505-多良木町/public-toilet"
    files = sorted(raw_dir.glob("*.csv"))
    if len(files) != 1:
        raise RuntimeError(f"多良木町: expected 1 raw CSV, got {len(files)}")

    src = files[0]
    enc = detect_text_encoding(src)
    with src.open("r", encoding=enc, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        missing = [c for c in schema if c not in header]
        if missing:
            raise RuntimeError(f"多良木町: missing standard columns: {missing}")
        rows = []
        for line_no, row in enumerate(reader, 2):
            clean = {k: (v or "").strip() for k, v in row.items()}
            if not any(clean.values()):
                continue
            out = {c: clean.get(c, "") for c in schema}
            legacy_code = clean.get("都道府県コード又は市区町村コード", "")
            legacy_pref = clean.get("都道府県名", "")
            legacy_city = clean.get("市区町村名", "")
            legacy_address = clean.get("住所", "")
            legacy_building = clean.get("方書", "")
            multipurpose = clean.get("多機能トイレ数", "")
            if legacy_code:
                if out["全国地方公共団体コード"] not in ("", legacy_code):
                    raise RuntimeError(f"多良木町 row {line_no}: code conflict")
                if out["所在地_全国地方公共団体コード"] not in ("", legacy_code):
                    raise RuntimeError(f"多良木町 row {line_no}: seat code conflict")
                out["全国地方公共団体コード"] = legacy_code
                out["所在地_全国地方公共団体コード"] = legacy_code
            if not out["地方公共団体名"] and legacy_city:
                out["地方公共団体名"] = legacy_city
            if not out["所在地_都道府県"] and legacy_pref:
                out["所在地_都道府県"] = legacy_pref
            if not out["建物名等(方書)"] and legacy_building:
                out["建物名等(方書)"] = legacy_building
            if legacy_address and legacy_address != out["所在地_連結表記"]:
                RowSupport.append_note(out, f"旧形式住所={legacy_address}")
            if multipurpose:
                RowSupport.append_note(out, f"原データ多機能トイレ数={multipurpose}")
            rows.append(out)
    if not rows:
        raise RuntimeError("多良木町: no non-empty data rows")
    dest = NORMALIZED / "43-熊本県/43505-多良木町/public-toilet/public-toilet.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=schema, lineterminator="\n")
        w.writeheader(); w.writerows(rows)
    tmp.replace(dest)
    print(f"OK 多良木町: rows={len(rows)} source={src.name} encoding={enc}")


def main():
    schema=read_schema_fields(SCHEMA_PATH)
    if len(schema)!=39:
        raise RuntimeError(f"expected 39 schema columns, got {len(schema)}")
    if "43505" in TARGETS:
        normalize_taragi(schema)


if __name__ == "__main__":
    main()
