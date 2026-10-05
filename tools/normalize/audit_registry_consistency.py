#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib
import pkgutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REGISTRY = ROOT / "tools/normalize/registry.csv"
MASTER = ROOT / "data/reference/municipalities.csv"
PREFECTURE_PACKAGE = "tools.normalize.prefectures"

Entry = tuple[str, str, str]


def _load_runner_entries() -> tuple[set[Entry], set[Entry], dict[str, str]]:
    package = importlib.import_module(PREFECTURE_PACKAGE)
    code_entries: set[Entry] = set()
    wildcard_entries: set[Entry] = set()
    prefecture_names: dict[str, str] = {}

    modules = sorted(
        info.name
        for info in pkgutil.iter_modules(package.__path__)
        if info.name.startswith("p") and info.name[1:3].isdigit()
    )

    for name in modules:
        module = importlib.import_module(f"{PREFECTURE_PACKAGE}.{name}")
        prefecture_code = str(module.PREFECTURE_CODE)
        prefecture_names[prefecture_code] = str(module.PREFECTURE_NAME)

        for handler in module.HANDLERS:
            if handler.codes:
                for code in handler.codes:
                    code_entries.add(("normalize", handler.module, str(code)))
            else:
                wildcard_entries.add(("normalize", handler.module, "*"))

    return code_entries, wildcard_entries, prefecture_names


def _load_master_names() -> dict[str, str]:
    if not MASTER.exists():
        return {}

    with MASTER.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    names: dict[str, str] = {}
    for row in rows:
        code = (row.get("municipality_code") or "").strip()
        name = (row.get("municipality_name") or "").strip()
        if code and name:
            names[code] = name
    return names


def _load_registry_entries(
    prefecture_names: dict[str, str],
    master_names: dict[str, str],
) -> tuple[set[Entry], set[Entry], list[str]]:
    code_entries: set[Entry] = set()
    wildcard_entries: set[Entry] = set()
    problems: list[str] = []

    with REGISTRY.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    for line_no, row in enumerate(rows, start=2):
        stage = (row.get("stage") or "").strip()
        if stage == "standard":
            continue
        if stage != "normalize":
            problems.append(f"line {line_no}: unknown stage={stage!r}")
            continue

        pref_code = (row.get("prefecture_code") or "").strip()
        pref_name = (row.get("prefecture_name") or "").strip()
        expected_pref_name = prefecture_names.get(pref_code)
        if expected_pref_name is None:
            problems.append(f"line {line_no}: unknown prefecture_code={pref_code!r}")
        elif pref_name != expected_pref_name:
            problems.append(
                f"line {line_no}: prefecture name mismatch: "
                f"{pref_code} registry={pref_name!r} runner={expected_pref_name!r}"
            )

        module = (row.get("module") or "").strip()
        codes_raw = (row.get("municipality_codes") or "").strip()
        names_raw = (row.get("municipality_names") or "").strip()

        if codes_raw == "*":
            if names_raw != "*":
                problems.append(
                    f"line {line_no}: wildcard codes require wildcard names: {names_raw!r}"
                )
            wildcard_entries.add((stage, module, "*"))
            continue

        codes = [x.strip() for x in codes_raw.split(";") if x.strip()]
        names = [x.strip() for x in names_raw.split(";") if x.strip()]
        if len(codes) != len(names):
            problems.append(
                f"line {line_no}: code/name count mismatch: "
                f"codes={len(codes)} names={len(names)}"
            )
            continue

        for code, name in zip(codes, names):
            if len(code) != 5 or not code.isdigit():
                problems.append(f"line {line_no}: invalid municipality code={code!r}")
                continue
            expected_name = master_names.get(code)
            if expected_name and name != expected_name:
                problems.append(
                    f"line {line_no}: municipality name mismatch: "
                    f"{code} registry={name!r} master={expected_name!r}"
                )
            code_entries.add((stage, module, code))

    return code_entries, wildcard_entries, problems


def _print_entries(title: str, entries: set[Entry]) -> None:
    if not entries:
        return
    print()
    print(title)
    for stage, module, code in sorted(entries):
        print(f"{stage},{module},{code}")


def main() -> int:
    runner_codes, runner_wildcards, prefecture_names = _load_runner_entries()
    master_names = _load_master_names()
    registry_codes, registry_wildcards, problems = _load_registry_entries(
        prefecture_names, master_names
    )

    runner_only_codes = runner_codes - registry_codes
    registry_only_codes = registry_codes - runner_codes
    runner_only_wildcards = runner_wildcards - registry_wildcards
    registry_only_wildcards = registry_wildcards - runner_wildcards

    print("===== SUMMARY =====")
    print(f"runner code entries   : {len(runner_codes)}")
    print(f"registry code entries : {len(registry_codes)}")
    print(f"common code entries   : {len(runner_codes & registry_codes)}")
    print(f"runner-only codes     : {len(runner_only_codes)}")
    print(f"registry-only codes   : {len(registry_only_codes)}")
    print()
    print(f"runner wildcards      : {len(runner_wildcards)}")
    print(f"registry wildcards    : {len(registry_wildcards)}")
    print(f"common wildcards      : {len(runner_wildcards & registry_wildcards)}")
    print(f"runner-only wildcards : {len(runner_only_wildcards)}")
    print(f"registry-only wildcard: {len(registry_only_wildcards)}")
    print()
    print(f"registry problems     : {len(problems)}")

    _print_entries("===== RUNNER ONLY: CODES =====", runner_only_codes)
    _print_entries("===== REGISTRY ONLY: CODES =====", registry_only_codes)
    _print_entries("===== RUNNER ONLY: WILDCARDS =====", runner_only_wildcards)
    _print_entries("===== REGISTRY ONLY: WILDCARDS =====", registry_only_wildcards)

    if problems:
        print()
        print("===== REGISTRY PROBLEMS =====")
        for problem in problems:
            print(problem)

    ok = not (
        runner_only_codes
        or registry_only_codes
        or runner_only_wildcards
        or registry_only_wildcards
        or problems
    )
    print()
    print("OK" if ok else "NG")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
