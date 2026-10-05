#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.normalization import RowSupport
from tools.normalize.core.schema import read_schema_fields

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"
SRC = ROOT / "data/raw/43-熊本県/43216-合志市/public-toilet/13_public_toilet.csv"
DEST = ROOT / "data/normalized/43-熊本県/43216-合志市/public-toilet/public-toilet.csv"

EXPECTED_META = {"推奨", "任意", "必須"}
CODE5 = "43216"



def main():
    if not SRC.exists():
        raise RuntimeError(f"raw missing: {SRC}")
    if DEST.exists():
        raise RuntimeError(f"normalized already exists: {DEST}")

    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    with SRC.open("r", encoding="utf-8-sig", newline="") as f:
        physical = list(csv.reader(f))

    if len(physical) < 2:
        raise RuntimeError("source must contain metadata header and standard header")

    meta_header = [v.strip() for v in physical[0]]
    real_header = [v.strip() for v in physical[1]]
    data_rows = physical[2:]

    if len(meta_header) != 39:
        raise RuntimeError(f"metadata header columns={len(meta_header)} expected=39")
    if set(meta_header) - EXPECTED_META:
        raise RuntimeError(
            f"unexpected metadata labels: {sorted(set(meta_header) - EXPECTED_META)!r}"
        )

    if real_header != schema:
        diffs = [
            (i, schema[i], real_header[i])
            for i in range(min(len(schema), len(real_header)))
            if schema[i] != real_header[i]
        ]
        raise RuntimeError(
            f"second row is not exact standard schema; "
            f"columns={len(real_header)} diffs={diffs[:20]!r}"
        )

    rows = []
    code6 = six_digit_municipality_code(CODE5)
    for line_no, values in enumerate(data_rows, 3):
        if len(values) != 39:
            raise RuntimeError(f"line {line_no}: columns={len(values)} expected=39")

        clean = [v.strip() for v in values]
        if not any(clean):
            continue

        row = dict(zip(schema, clean))

        if row["全国地方公共団体コード"] != CODE5:
            raise RuntimeError(
                f"line {line_no}: unexpected municipality code "
                f"{row['全国地方公共団体コード']!r}"
            )
        if row["所在地_全国地方公共団体コード"] != CODE5:
            raise RuntimeError(
                f"line {line_no}: unexpected location municipality code "
                f"{row['所在地_全国地方公共団体コード']!r}"
            )

        RowSupport.append_note(row, f"原データ全国地方公共団体コード={CODE5}")
        RowSupport.append_note(row, f"原データ所在地_全国地方公共団体コード={CODE5}")
        row["全国地方公共団体コード"] = code6
        row["所在地_全国地方公共団体コード"] = code6
        rows.append(row)

    if not rows:
        raise RuntimeError("no non-empty data rows")

    ids = [r["ID"] for r in rows if r["ID"]]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate nonblank IDs found")

    print("preflight OK: 合志市")
    print(
        f"rows={len(rows)} exact_second_row_schema=True "
        f"municipality_code={code6}"
    )

    DEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = DEST.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=schema, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(DEST)

    print(f"OK 合志市: rows={len(rows)} encoding=utf-8-sig")


if __name__ == "__main__":
    main()
