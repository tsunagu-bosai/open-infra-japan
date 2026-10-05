#!/usr/bin/env python3

import argparse
import csv
import re
from collections import Counter
from datetime import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
NORMALIZED_DIR = ROOT / "data" / "normalized"
REFERENCE_MUNICIPALITIES = ROOT / "data" / "reference" / "municipalities.csv"
SCHEMA_FILE = ROOT / "schema" / "standard" / "public-toilet" / "schema.csv"

COUNT_COLUMNS = [
    "男性トイレ総数", "男性トイレ数（小便器）", "男性トイレ数（和式）",
    "男性トイレ数（洋式）", "女性トイレ総数", "女性トイレ数（和式）",
    "女性トイレ数（洋式）", "男女共用トイレ総数", "男女共用トイレ数（和式）",
    "男女共用トイレ数（洋式）", "バリアフリートイレ数",
]

BOOLEAN_COLUMNS = [
    "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無",
]

TIME_COLUMNS = ["利用開始時間", "利用終了時間"]

# Definition sheet specifies 時刻（hh:mm）.
# 24:00 is retained as a warning-compatible source representation rather than
# silently normalizing it here.
TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")



def normalize_classification(value):
    value = (value or "").strip()
    if value == "◎":
        return "required"
    if value in {"○", "〇"}:
        return "recommended"
    return "optional"


def load_schema():
    with SCHEMA_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if len(rows) != 39:
        raise ValueError(f"Expected 39 schema rows, got {len(rows)}")

    for row in rows:
        row["classification_normalized"] = normalize_classification(
            row.get("classification")
        )
    return rows


def make_local_government_code(code5):
    if len(code5) != 5 or not code5.isdigit():
        raise ValueError(f"Invalid municipality code: {code5}")

    digits = [int(char) for char in code5]
    weighted_sum = (
        digits[0] * 6 + digits[1] * 5 + digits[2] * 4
        + digits[3] * 3 + digits[4] * 2
    )
    remainder = weighted_sum % 11

    if remainder <= 1:
        check_digit = (11 - remainder) % 10
    else:
        check_digit = 11 - remainder

    return code5 + str(check_digit)


def read_csv_file(path, encoding):
    with path.open("r", encoding=encoding, newline="") as f:
        return list(csv.DictReader(f))


def detect_csv_encoding(path):
    with path.open("rb") as f:
        prefix = f.read(4)

    if prefix.startswith(b"\xef\xbb\xbf"):
        candidates = ["utf-8-sig"]
    elif prefix.startswith(b"\xff\xfe") or prefix.startswith(b"\xfe\xff"):
        candidates = ["utf-16"]
    else:
        candidates = ["utf-8", "cp932"]

    for encoding in candidates:
        try:
            return encoding, read_csv_file(path, encoding)
        except UnicodeDecodeError:
            continue

    return None, []


def read_xlsx_file(path):
    from openpyxl import load_workbook

    workbook = load_workbook(path, read_only=True, data_only=True)
    worksheet = workbook.active
    iterator = worksheet.iter_rows(values_only=True)
    header_row = next(iterator, None)

    if header_row is None:
        workbook.close()
        return []

    header = ["" if value is None else str(value) for value in header_row]
    rows = []

    for values in iterator:
        row = {}
        for index, column in enumerate(header):
            value = values[index] if index < len(values) else None
            if isinstance(value, time):
                row[column] = value.strftime("%H:%M")
            else:
                row[column] = "" if value is None else str(value).strip()
        rows.append(row)

    workbook.close()
    return rows


def load_dataset(path):
    suffix = path.suffix.lower()
    if suffix == ".csv":
        encoding, rows = detect_csv_encoding(path)
        if encoding is None:
            raise ValueError("CSV encoding could not be detected")
        return encoding, rows
    if suffix == ".xlsx":
        return "-", read_xlsx_file(path)
    raise ValueError(f"Unsupported format: {suffix}")


def is_number(value):
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def is_nonnegative_integer(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return number >= 0 and number.is_integer()


def is_standard_time(value):
    return bool(TIME_PATTERN.fullmatch(value))


def add_issue(result, severity, key, count=1):
    result["issues"][severity][key] += count


def validate_dataset(municipality, path, schema):
    encoding, rows = load_dataset(path)

    municipality_code = municipality["municipality_code"].strip()
    official_municipality_code = make_local_government_code(municipality_code)
    expected_columns = [row["name"] for row in schema]
    required_columns = [
        row["name"] for row in schema
        if row["classification_normalized"] == "required"
    ]

    result = {
        "municipality_code": municipality_code,
        "official_municipality_code": official_municipality_code,
        "municipality_name": municipality["municipality_name"].strip(),
        "file": path.name,
        "encoding": encoding,
        "rows": len(rows),
        "columns_ok": True,
        "missing_columns": [],
        "extra_columns": [],
        "required_blank": Counter(),
        "municipality_code_blank": 0,
        "municipality_code_invalid_format": 0,
        "municipality_code_mismatch": 0,
        "id_blank": 0,
        "id_duplicate": 0,
        "latitude_blank": 0,
        "latitude_invalid": 0,
        "longitude_blank": 0,
        "longitude_invalid": 0,
        "count_invalid": Counter(),
        "boolean_invalid": Counter(),
        "time_invalid": Counter(),
        "boolean_values": {column: Counter() for column in BOOLEAN_COLUMNS},
        "time_values": {column: Counter() for column in TIME_COLUMNS},
        "issues": {
            "ERROR": Counter(),
            "WARNING": Counter(),
            "INFO": Counter(),
        },
    }

    if not rows:
        add_issue(result, "WARNING", "dataset has no rows")
        return result

    actual_columns = list(rows[0].keys())
    result["missing_columns"] = [
        column for column in expected_columns if column not in actual_columns
    ]
    result["extra_columns"] = [
        column for column in actual_columns if column not in expected_columns
    ]
    result["columns_ok"] = actual_columns == expected_columns

    if not result["columns_ok"]:
        add_issue(result, "ERROR", "39-column schema mismatch")

    seen_ids = set()

    for row in rows:
        for column in required_columns:
            value = (row.get(column, "") or "").strip()
            if not value:
                result["required_blank"][column] += 1

        code = (row.get("全国地方公共団体コード", "") or "").strip()
        if not code:
            result["municipality_code_blank"] += 1
        elif not (len(code) == 6 and code.isascii() and code.isdigit()):
            result["municipality_code_invalid_format"] += 1
        elif code != official_municipality_code:
            result["municipality_code_mismatch"] += 1

        record_id = (row.get("ID", "") or "").strip()
        if not record_id:
            result["id_blank"] += 1
        else:
            if record_id in seen_ids:
                result["id_duplicate"] += 1
            else:
                seen_ids.add(record_id)

        latitude = (row.get("緯度", "") or "").strip()
        if not latitude:
            result["latitude_blank"] += 1
        elif not is_number(latitude) or not -90 <= float(latitude) <= 90:
            result["latitude_invalid"] += 1

        longitude = (row.get("経度", "") or "").strip()
        if not longitude:
            result["longitude_blank"] += 1
        elif not is_number(longitude) or not -180 <= float(longitude) <= 180:
            result["longitude_invalid"] += 1

        for column in COUNT_COLUMNS:
            value = (row.get(column, "") or "").strip()
            if value and not is_nonnegative_integer(value):
                result["count_invalid"][column] += 1

        for column in BOOLEAN_COLUMNS:
            value = (row.get(column, "") or "").strip()
            result["boolean_values"][column][value or "(blank)"] += 1
            if value and value not in {"有", "無"}:
                result["boolean_invalid"][column] += 1

        for column in TIME_COLUMNS:
            value = (row.get(column, "") or "").strip()
            result["time_values"][column][value or "(blank)"] += 1
            if value and not is_standard_time(value):
                result["time_invalid"][column] += 1

    # ERROR: explicit rule violations / structurally unusable values.
    if result["municipality_code_invalid_format"]:
        add_issue(
            result, "ERROR", "invalid municipality code format",
            result["municipality_code_invalid_format"]
        )
    if result["municipality_code_mismatch"]:
        add_issue(
            result, "ERROR", "municipality code mismatch",
            result["municipality_code_mismatch"]
        )
    if result["id_duplicate"]:
        add_issue(result, "WARNING", "duplicate ID", result["id_duplicate"])
    for column, count in result["count_invalid"].items():
        add_issue(result, "ERROR", f"invalid numeric value: {column}", count)
    for column, count in result["boolean_invalid"].items():
        add_issue(result, "ERROR", f"invalid controlled vocabulary: {column}", count)

    # INFO: the official notes allow an otherwise useful row to remain even
    # when a required field is difficult to fill. Keep required-field blanks
    # visible as completeness observations, not warnings.
    for column, count in result["required_blank"].items():
        add_issue(result, "INFO", f"blank required field: {column}", count)

    # WARNING: representation differs from hh:mm or coordinates fail sanity checks.
    for column, count in result["time_invalid"].items():
        add_issue(result, "WARNING", f"time not in hh:mm form: {column}", count)
    if result["latitude_invalid"]:
        add_issue(
            result, "WARNING", "invalid latitude", result["latitude_invalid"]
        )
    if result["longitude_invalid"]:
        add_issue(
            result, "WARNING", "invalid longitude", result["longitude_invalid"]
        )

    # INFO: recommended-field absence / quality observations.
    if result["municipality_code_blank"]:
        add_issue(
            result, "INFO", "blank municipality code",
            result["municipality_code_blank"]
        )
    if result["id_blank"]:
        add_issue(result, "INFO", "blank ID", result["id_blank"])
    if result["latitude_blank"]:
        add_issue(
            result, "INFO", "blank latitude", result["latitude_blank"]
        )
    if result["longitude_blank"]:
        add_issue(
            result, "INFO", "blank longitude", result["longitude_blank"]
        )

    return result


def print_counter(counter, limit=20):
    if not counter:
        print("    (none)")
        return
    for value, count in counter.most_common(limit):
        print(f"    {value!r}: {count}")
    if len(counter) > limit:
        print(f"    ... {len(counter) - limit} more values")


def print_issue_summary(result):
    print("  severity summary:")
    for severity in ("ERROR", "WARNING", "INFO"):
        issues = result["issues"][severity]
        total = sum(issues.values())
        print(f"    {severity:<7}: {total}")
        for label, count in issues.items():
            print(f"      - {label}: {count}")


def print_result(result):
    print(
        f"{result['municipality_code']} "
        f"{result['municipality_name']} {result['file']}"
    )
    print(f"  rows                     : {result['rows']}")
    print(f"  encoding                 : {result['encoding']}")
    print(f"  exact 39-column schema   : {result['columns_ok']}")

    if result["missing_columns"]:
        print("  missing columns          : " + " | ".join(result["missing_columns"]))
    if result["extra_columns"]:
        print("  extra columns            : " + " | ".join(result["extra_columns"]))

    print(f"  municipality code blank : {result['municipality_code_blank']}")
    print(
        "  municipality code invalid: "
        f"{result['municipality_code_invalid_format']}"
    )
    print(
        "  municipality code mismatch: "
        f"{result['municipality_code_mismatch']}"
    )
    print(f"  blank ID                 : {result['id_blank']}")
    print(f"  duplicate ID             : {result['id_duplicate']}")

    print("  blank required fields:")
    if result["required_blank"]:
        for column, count in result["required_blank"].items():
            print(f"    {column}: {count}")
    else:
        print("    (none)")

    print(f"  blank latitude           : {result['latitude_blank']}")
    print(f"  invalid latitude         : {result['latitude_invalid']}")
    print(f"  blank longitude          : {result['longitude_blank']}")
    print(f"  invalid longitude        : {result['longitude_invalid']}")

    print("  invalid count values:")
    if result["count_invalid"]:
        for column, count in result["count_invalid"].items():
            print(f"    {column}: {count}")
    else:
        print("    (none)")

    print("  invalid boolean values:")
    if result["boolean_invalid"]:
        for column, count in result["boolean_invalid"].items():
            print(f"    {column}: {count}")
    else:
        print("    (none)")

    print("  boolean-like values:")
    for column in BOOLEAN_COLUMNS:
        print(f"    [{column}]")
        print_counter(result["boolean_values"][column])

    print("  non-hh:mm time values:")
    if result["time_invalid"]:
        for column, count in result["time_invalid"].items():
            print(f"    {column}: {count}")
    else:
        print("    (none)")

    print("  time values:")
    for column in TIME_COLUMNS:
        print(f"    [{column}]")
        print_counter(result["time_values"][column])

    print_issue_summary(result)
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--prefecture", help="都道府県コード（例: 13）。省略時は全国"
    )
    parser.add_argument(
        "--input",
        choices=("raw", "normalized"),
        default="raw",
        help="検証対象（既定: raw）",
    )
    args = parser.parse_args()
    schema = load_schema()

    with REFERENCE_MUNICIPALITIES.open(
        "r", encoding="utf-8-sig", newline=""
    ) as f:
        reference_rows = list(csv.DictReader(f))

    reference_map = {
        row["municipality_code"].strip(): row
        for row in reference_rows
        if row.get("municipality_code")
    }

    input_root = RAW_DIR if args.input == "raw" else NORMALIZED_DIR
    results = []

    prefecture_dirs = sorted(
        path for path in input_root.iterdir()
        if path.is_dir()
        and len(path.name) >= 3
        and path.name[:2].isdigit()
        and path.name[2:3] == "-"
        and (not args.prefecture or path.name[:2] == args.prefecture)
    ) if input_root.exists() else []

    for prefecture_dir in prefecture_dirs:
        prefecture_code = prefecture_dir.name[:2]
        municipality_dirs = sorted(
            path for path in prefecture_dir.iterdir()
            if path.is_dir()
            and len(path.name) >= 6
            and path.name[:5].isdigit()
            and path.name[5:6] == "-"
        )

        for municipality_dir in municipality_dirs:
            municipality_code = municipality_dir.name[:5]
            municipality = reference_map.get(municipality_code)
            if not municipality:
                print(
                    f"ERROR: unknown municipality directory: "
                    f"{municipality_dir.relative_to(ROOT)}"
                )
                continue

            if municipality["prefecture_code"].strip() != prefecture_code:
                print(
                    f"ERROR: prefecture mismatch: "
                    f"{municipality_dir.relative_to(ROOT)}"
                )
                continue

            directory = municipality_dir / "public-toilet"
            if not directory.exists():
                continue

            files = sorted(
                path for path in directory.iterdir()
                if path.is_file()
                and path.suffix.lower() in {".csv", ".xlsx"}
            )

            for path in files:
                try:
                    result = validate_dataset(municipality, path, schema)
                except Exception as exc:
                    print(
                        f"ERROR: {municipality['municipality_name']} "
                        f"{path.name}: {exc}"
                    )
                    continue
                results.append(result)

    print()
    print(f"Datasets validated: {len(results)}")
    print()

    totals = Counter()
    for result in results:
        print_result(result)
        for severity in ("ERROR", "WARNING", "INFO"):
            totals[severity] += sum(result["issues"][severity].values())

    print("Overall severity totals:")
    for severity in ("ERROR", "WARNING", "INFO"):
        print(f"  {severity:<7}: {totals[severity]}")


if __name__ == "__main__":
    main()
