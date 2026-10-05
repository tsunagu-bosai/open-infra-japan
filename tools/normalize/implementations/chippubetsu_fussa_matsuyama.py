#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path
from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.normalization import RowSupport, StandardCsvWriter
from tools.normalize.core.encoding import detect_text_encoding

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"
GENERIC = ROOT / "tools/normalize_public_toilet.py"

TARGETS = {
    "13218": {
        "pref": "13-東京都",
        "mun": "13218-福生市",
        "file": "20260801_13.csv",
        "extra": None,
        "extra_mode": "none",
    },
    "38201": {
        "pref": "38-愛媛県",
        "mun": "38201-松山市",
        "file": "382019_public_toilet_202510.csv",
        "extra": "多機能トイレ数",
        "extra_mode": "blank_only",
    },
    "01434": {
        "pref": "01-北海道",
        "mun": "01434-秩父別町",
        "file": "014346_public_toilet-6601.csv",
        "extra": "多機能トイレ数",
        "extra_mode": "preserve",
    },
}


def load_generic():
    spec = importlib.util.spec_from_file_location("normalize_public_toilet", GENERIC)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod



def read_target(code, cfg, schema, generic):
    src = ROOT / "data/raw" / cfg["pref"] / cfg["mun"] / "public-toilet" / cfg["file"]
    if not src.exists():
        raise RuntimeError(f"{code}: missing raw file: {src}")

    enc = detect_text_encoding(src)
    with src.open("r", encoding=enc, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []

        missing = [c for c in schema if c not in header]
        if missing:
            raise RuntimeError(f"{code}: missing schema columns: {missing}")

        extras = [c for c in header if c not in schema]
        expected_extra = cfg["extra"]

        if cfg["extra_mode"] == "none":
            if extras:
                raise RuntimeError(f"{code}: unexpected extras: {extras!r}")
        else:
            if extras != [expected_extra]:
                raise RuntimeError(
                    f"{code}: extras actual={extras!r} expected={[expected_extra]!r}"
                )

        rows = []
        extra_nonempty = 0

        for line_no, srcrow in enumerate(reader, 2):
            clean = {k: (v or "").strip() for k, v in srcrow.items()}
            if not any(clean.values()):
                continue

            row = {c: clean.get(c, "") for c in schema}

            if cfg["extra_mode"] == "blank_only":
                v = clean.get(expected_extra, "")
                if v:
                    raise RuntimeError(
                        f"{code}:{line_no}: expected blank {expected_extra}, got {v!r}"
                    )

            elif cfg["extra_mode"] == "preserve":
                v = clean.get(expected_extra, "")
                if v:
                    RowSupport.append_note(row, f"原データ{expected_extra}={v}")
                    extra_nonempty += 1

            row["利用開始時間"] = generic.normalize_time(row["利用開始時間"])
            row["利用終了時間"] = generic.normalize_time(row["利用終了時間"])

            rows.append(row)

    dest = ROOT / "data/normalized" / cfg["pref"] / cfg["mun"] / "public-toilet/public-toilet.csv"
    if dest.exists():
        raise RuntimeError(f"{code}: normalized output already exists: {dest}")

    return src, dest, rows, enc, extra_nonempty



def main():
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"expected 39 schema columns, got {len(schema)}")

    generic = load_generic()
    prepared = []

    for code, cfg in TARGETS.items():
        prepared.append((code, cfg, *read_target(code, cfg, schema, generic)))

    print(f"preflight OK: {len(prepared)} municipalities")

    for code, cfg, src, dest, rows, enc, preserved in prepared:
        StandardCsvWriter().write(dest, schema, rows)
        suffix = f" preserved_extra={preserved}" if preserved else ""
        print(
            f"OK {code} {cfg['mun']}: rows={len(rows)} "
            f"source={src.name} encoding={enc}{suffix}"
        )


if __name__ == "__main__":
    main()
