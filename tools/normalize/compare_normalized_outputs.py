#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


TARGET_NAME = "public-toilet.csv"


def collect(root: Path) -> dict[Path, Path]:
    return {
        path.relative_to(root): path
        for path in sorted(root.rglob(TARGET_NAME))
        if path.is_file()
    }


def read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return [], []

    return rows[0], rows[1:]


def semantic_equal(expected: Path, actual: Path) -> bool:
    try:
        return read_csv(expected) == read_csv(actual)
    except (UnicodeDecodeError, csv.Error):
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="再生成した公衆トイレCSVを既存normalized成果物と比較"
    )
    parser.add_argument(
        "--expected",
        type=Path,
        default=Path("data/normalized"),
        help="基準となるnormalizedルート",
    )
    parser.add_argument(
        "--actual",
        type=Path,
        required=True,
        help="再生成結果のnormalizedルート",
    )
    args = parser.parse_args()

    expected_root = args.expected.resolve()
    actual_root = args.actual.resolve()

    if not expected_root.is_dir():
        parser.error(f"--expected が存在しません: {expected_root}")

    if not actual_root.is_dir():
        parser.error(f"--actual が存在しません: {actual_root}")

    expected = collect(expected_root)
    actual = collect(actual_root)

    expected_keys = set(expected)
    actual_keys = set(actual)

    missing = sorted(expected_keys - actual_keys)
    extra = sorted(actual_keys - expected_keys)

    same: list[Path] = []
    changed: list[tuple[Path, bool]] = []

    for rel in sorted(expected_keys & actual_keys):
        expected_path = expected[rel]
        actual_path = actual[rel]

        if expected_path.read_bytes() == actual_path.read_bytes():
            same.append(rel)
            continue

        changed.append(
            (rel, semantic_equal(expected_path, actual_path))
        )

    print("===== SUMMARY =====")
    print(f"SAME    : {len(same)}")
    print(f"CHANGED : {len(changed)}")
    print(f"MISSING : {len(missing)}")
    print(f"EXTRA   : {len(extra)}")

    if changed:
        print()
        print("===== CHANGED =====")
        for rel, semantic_same in changed:
            status = "same" if semantic_same else "changed"
            print(f"{rel}  semantic={status}")

    if missing:
        print()
        print("===== MISSING =====")
        for rel in missing:
            print(rel)

    if extra:
        print()
        print("===== EXTRA =====")
        for rel in extra:
            print(rel)

    ok = not changed and not missing and not extra

    print()
    print("OK" if ok else "NG")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
