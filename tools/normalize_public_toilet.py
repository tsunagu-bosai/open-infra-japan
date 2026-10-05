#!/usr/bin/env python3
"""
Normalize public-toilet datasets without modifying source files.

Input:
  data/raw/<prefecture>/<municipality>/public-toilet/*.(csv|xlsx)

Output:
  data/normalized/<prefecture>/<municipality>/public-toilet/public-toilet.csv

Normalization:
- output UTF-8 with BOM CSV
- output columns follow schema/standard/public-toilet/schema.csv
- XLSX datetime.time -> HH:MM
- safe time representation normalization:
    H:MM      -> HH:MM
    H:MM:SS  -> HH:MM only when SS == 00
    24:00:00 -> 24:00
    Excel serial fractions in CSV -> HH:MM
- apply patches/public-toilet/<prefecture>/<municipality>.csv
  only when municipality_code, ID, field and original_value all match.

It does NOT guess or repair ambiguous source values.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.municipality import six_digit_municipality_code

RAW_ROOT = ROOT / "data" / "raw"
NORMALIZED_ROOT = ROOT / "data" / "normalized"
PATCH_ROOT = ROOT / "patches" / "public-toilet"
SCHEMA_PATH = ROOT / "schema" / "standard" / "public-toilet" / "schema.csv"

TIME_FIELDS = {"利用開始時間", "利用終了時間"}
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "cp932", "utf-16")


def read_schema() -> list[str]:
    with SCHEMA_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return [r["name"] for r in csv.DictReader(f)]


def detect_csv_encoding(path: Path) -> str:
    for enc in CSV_ENCODINGS:
        try:
            with path.open("r", encoding=enc, newline="") as f:
                f.read(8192)
            return enc
        except UnicodeError:
            continue
    raise ValueError(f"Unable to detect encoding: {path}")


def stringify(value) -> str:
    if value is None:
        return ""
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return str(value).strip()


def read_csv(path: Path) -> tuple[list[dict[str, str]], str]:
    enc = detect_csv_encoding(path)
    with path.open("r", encoding=enc, newline="") as f:
        rows = []
        for raw_row in csv.DictReader(f):
            row = {str(k).strip(): stringify(v) for k, v in raw_row.items()}
            if not any(row.values()):
                continue
            rows.append(row)
    return rows, enc


def read_xlsx(path: Path) -> tuple[list[dict[str, str]], str]:
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb.active
        it = ws.iter_rows(values_only=True)
        header = [stringify(v) for v in next(it)]
        rows = []
        for values in it:
            row = {}
            for i, name in enumerate(header):
                if not name:
                    continue
                value = values[i] if i < len(values) else None
                row[name] = stringify(value)
            if not any(row.values()):
                continue
            rows.append(row)
        return rows, "xlsx"
    finally:
        wb.close()


def read_source_header(path: Path) -> list[str]:
    """Read only the source header for safe exact-schema detection."""
    if path.suffix.lower() == ".csv":
        enc = detect_csv_encoding(path)
        with path.open("r", encoding=enc, newline="") as f:
            return [stringify(v) for v in next(csv.reader(f), [])]
    if path.suffix.lower() == ".xlsx":
        from openpyxl import load_workbook
        wb = load_workbook(path, read_only=True, data_only=True)
        try:
            ws = wb.active
            values = next(ws.iter_rows(values_only=True), ())
            return [stringify(v) for v in values]
        finally:
            wb.close()
    return []


_HM = re.compile(r"^(\d{1,2}):(\d{2})$")
_HMS = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2})$")
_DECIMAL = re.compile(r"^(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?$")


def normalize_time(value: str) -> str:
    """Normalize representation only; do not infer opening semantics."""
    s = value.strip()
    if not s:
        return ""

    m = _HM.fullmatch(s)
    if m:
        h, minute = map(int, m.groups())
        if 0 <= h <= 24 and 0 <= minute <= 59 and not (h == 24 and minute != 0):
            return f"{h:02d}:{minute:02d}"
        return s

    m = _HMS.fullmatch(s)
    if m:
        h, minute, second = map(int, m.groups())
        if second == 0 and 0 <= h <= 24 and 0 <= minute <= 59 and not (h == 24 and minute != 0):
            return f"{h:02d}:{minute:02d}"
        return s

    # CSV exported from an Excel time cell can contain a day fraction.
    # Only [0,1) is treated as an Excel time serial. This intentionally
    # excludes 1 and larger values.
    if _DECIMAL.fullmatch(s):
        try:
            d = Decimal(s)
        except InvalidOperation:
            return s
        if Decimal("0") <= d < Decimal("1"):
            total_minutes = int(
                (d * Decimal(24 * 60)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            )
            total_minutes %= 24 * 60
            return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"

    return s


def load_patches(pref_dir: str, municipality_dir: str) -> list[dict[str, str]]:
    path = PATCH_ROOT / pref_dir / f"{municipality_dir}.csv"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def apply_patches(
    rows: list[dict[str, str]],
    patches: list[dict[str, str]],
    source: Path,
) -> tuple[int, list[str]]:
    applied = 0
    problems = []

    for p in patches:
        pid = (p.get("id") or "").strip()
        match_field = (p.get("match_field") or "").strip()
        match_value = (p.get("match_value") or "").strip()
        field = (p.get("field") or "").strip()
        original = (p.get("original_value") or "").strip()
        patched = (p.get("patched_value") or "").strip()

        # Backward compatibility: existing patches identify a row by ID.
        selector_field = match_field or "ID"
        selector_value = match_value if match_field else pid
        selector = f"{selector_field}={selector_value!r}"

        if not rows or selector_field not in rows[0]:
            problems.append(
                f"{source}: patch {selector}: unknown selector field"
            )
            continue

        matches = [
            row for row in rows
            if (row.get(selector_field) or "").strip() == selector_value
        ]
        if len(matches) != 1:
            problems.append(
                f"{source}: patch {selector}: expected 1 row, found {len(matches)}"
            )
            continue

        row = matches[0]
        if field not in row:
            problems.append(
                f"{source}: patch {selector}: unknown field {field!r}"
            )
            continue

        current = row[field]
        if current != original:
            problems.append(
                f"{source}: patch {selector} field={field!r}: "
                f"original mismatch (source={current!r}, patch={original!r})"
            )
            continue

        row[field] = patched
        applied += 1

    return applied, problems


def find_source_files(prefecture: str | None) -> list[Path]:
    paths = []
    for p in RAW_ROOT.glob("*/*/public-toilet/*"):
        if p.suffix.lower() not in {".csv", ".xlsx"}:
            continue
        pref_dir = p.parents[2].name
        if prefecture and not pref_dir.startswith(f"{prefecture}-"):
            continue
        paths.append(p)
    return sorted(paths)

def source_identity(path: Path) -> list[tuple[str, str]]:
    if path.suffix.lower() == ".csv":
        rows, _ = read_csv(path)
    elif path.suffix.lower() == ".xlsx":
        rows, _ = read_xlsx(path)
    else:
        raise RuntimeError(f"unsupported source format: {path}")

    return [
        (
            (row.get("ID") or "").strip(),
            (row.get("名称") or "").strip(),
        )
        for row in rows
    ]

def select_source_files(
    files: list[Path],
    schema: list[str],
    only_standard: bool,
    overwrite: bool,
) -> list[Path]:
    by_municipality: dict[Path, list[Path]] = {}

    for path in files:
        pref_dir = path.parents[2].name
        municipality_dir = path.parents[1]
        out_path = (
            NORMALIZED_ROOT
            / pref_dir
            / municipality_dir.name
            / "public-toilet"
            / "public-toilet.csv"
        )

        if out_path.exists() and not overwrite:
            continue

        if only_standard and read_source_header(path) != schema:
            continue

        by_municipality.setdefault(municipality_dir, []).append(path)

    selected = []

    for municipality_dir in sorted(by_municipality):
        candidates = sorted(by_municipality[municipality_dir])

        if len(candidates) == 1:
            selected.append(candidates[0])
            continue

        csvs = [p for p in candidates if p.suffix.lower() == ".csv"]
        xlsxs = [p for p in candidates if p.suffix.lower() == ".xlsx"]

        if len(candidates) == 2 and len(csvs) == 1 and len(xlsxs) == 1:
            csv_path = csvs[0]
            xlsx_path = xlsxs[0]

            if source_identity(csv_path) == source_identity(xlsx_path):
                print(
                    f"SELECT canonical CSV: {municipality_dir} "
                    f"({csv_path.name}; equivalent XLSX={xlsx_path.name})"
                )
                selected.append(csv_path)
                continue

        raise RuntimeError(
            f"{municipality_dir}: multiple standard source files require "
            f"explicit handling: {[p.name for p in candidates]!r}"
        )

    return selected

def append_note(row: dict[str, str], text: str) -> None:
    text = (text or "").strip()
    if not text:
        return

    current = (row.get("備考") or "").strip()
    row["備考"] = f"{current} / {text}" if current else text


def normalize_publisher_municipality_code(
    row: dict[str, str],
    municipality_dir: str,
) -> None:
    code5 = municipality_dir[:5]
    if len(code5) != 5 or not code5.isdigit():
        raise RuntimeError(
            f"{municipality_dir}: invalid municipality directory"
        )

    expected = six_digit_municipality_code(code5)

    for field in (
        "全国地方公共団体コード",
        "所在地_全国地方公共団体コード",
    ):
        raw = (row.get(field) or "").strip()

        if not raw:
            continue

        if raw == expected:
            continue

        # Spreadsheet/CSV export may drop a leading zero from a 6-digit code.
        if raw.zfill(6) == expected:
            append_note(row, f"原データ{field}={raw}")
            row[field] = expected
            continue

        raise RuntimeError(
            f"{municipality_dir}: {field}={raw!r} "
            f"does not match expected {expected!r}"
        )


def normalize_file(path: Path, schema: list[str], overwrite: bool, only_standard: bool = False) -> tuple[int, int]:
    pref_dir = path.parents[2].name
    municipality_dir = path.parents[1].name

    out_dir = NORMALIZED_ROOT / pref_dir / municipality_dir / "public-toilet"
    out_path = out_dir / "public-toilet.csv"

    if out_path.exists() and not overwrite:
        print(f"SKIP existing: {out_path}")
        return 0, 0

    if only_standard:
        source_header = read_source_header(path)
        if source_header != schema:
            print(f"SKIP non-standard schema: {path}")
            return 0, 0

    if path.suffix.lower() == ".csv":
        rows, source_format = read_csv(path)
    else:
        rows, source_format = read_xlsx(path)

    # Keep only the official 39 columns, in official order.
    normalized = []
    for row in rows:
        out = {name: row.get(name, "") for name in schema}

        for field in TIME_FIELDS:
            out[field] = normalize_time(out[field])

        normalized.append(out)

    # Source corrections must run before semantic validation. A patch is
    # applied only when both its selector and original value match exactly.
    patches = load_patches(pref_dir, municipality_dir)
    applied, problems = apply_patches(normalized, patches, path)

    if problems:
        for msg in problems:
            print(f"PATCH ERROR: {msg}", file=sys.stderr)
        raise RuntimeError(f"Patch verification failed for {path}")

    for out in normalized:
        normalize_publisher_municipality_code(out, municipality_dir)

    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=schema, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        writer.writerows(normalized)
    tmp.replace(out_path)

    print(
        f"OK {municipality_dir}: rows={len(normalized)} "
        f"source={source_format} patches={applied} -> {out_path}"
    )
    return len(normalized), applied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--prefecture",
        help="prefecture code, e.g. 13",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="overwrite existing normalized files",
    )
    parser.add_argument(
        "--only-standard",
        action="store_true",
        help="process only sources whose header exactly matches the official 39-column schema",
    )
    parser.add_argument(
        "--exclude-code",
        action="append",
        default=[],
        help="exclude municipality code from processing; may be specified multiple times",
    )
    args = parser.parse_args()

    schema = read_schema()
    if len(schema) != 39:
        raise RuntimeError(f"Expected 39 schema columns, got {len(schema)}")

    source_files = find_source_files(args.prefecture)

    exclude_codes = set(args.exclude_code)
    if exclude_codes:
        source_files = [
            path
            for path in source_files
            if path.parents[1].name.split("-", 1)[0] not in exclude_codes
        ]

    if not source_files:
        if args.only_standard:
            print("No standard source files found; nothing to do.")
            return 0

        print("No source files found.", file=sys.stderr)
        return 1

    files = select_source_files(
        source_files,
        schema,
        args.only_standard,
        args.overwrite,
    )

    if not files:
        print("No matching standard source files found; nothing to do.")
        return 0

    total_rows = 0
    total_patches = 0
    for path in files:
        rows, patches = normalize_file(path, schema, args.overwrite, args.only_standard)
        total_rows += rows
        total_patches += patches

    print(
        f"\nNormalized files: {len(files)}"
        f"\nRows written    : {total_rows}"
        f"\nPatches applied : {total_patches}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
