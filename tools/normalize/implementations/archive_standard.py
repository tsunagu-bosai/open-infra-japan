#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path
from typing import Any

from tools.normalize.core.normalization import StandardCsvWriter
from tools.normalize.core.schema import read_schema_fields
from tools import normalize_public_toilet as common


ROOT = Path.cwd()
RAW = ROOT / "data/raw"
OUT = ROOT / "data/normalized"
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"


TARGETS: dict[str, dict[str, Any]] = {
    "13117": {
        "prefecture_dir": "13-東京都",
        "municipality_dir": "13117-北区",
        "archive": "hyo-jun.zip",
        "member": "13.公衆トイレ一覧.csv",
        "code6": "131172",
    },
}


def _read_archive_member(
    archive_path: Path,
    member_name: str,
    schema: list[str],
) -> list[dict[str, str]]:
    if not archive_path.is_file():
        raise RuntimeError(f"archive not found: {archive_path}")

    with zipfile.ZipFile(archive_path) as archive:
        matches = [name for name in archive.namelist() if name == member_name]
        if len(matches) != 1:
            raise RuntimeError(
                f"{archive_path}: member count={len(matches)} expected=1: {member_name!r}"
            )

        raw = archive.read(member_name)

    if not raw.startswith(b"\xef\xbb\xbf"):
        raise RuntimeError(f"{archive_path}!{member_name}: expected UTF-8 BOM")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            f"{archive_path}!{member_name}: cannot decode as utf-8-sig"
        ) from exc

    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise RuntimeError(f"{archive_path}!{member_name}: empty CSV") from exc

    if header != schema:
        missing = [name for name in schema if name not in header]
        extra = [name for name in header if name not in schema]
        raise RuntimeError(
            f"{archive_path}!{member_name}: schema mismatch "
            f"columns={len(header)} expected={len(schema)} "
            f"missing={missing!r} extra={extra!r}"
        )

    rows: list[dict[str, str]] = []
    for line_no, values in enumerate(reader, start=2):
        if len(values) != len(schema):
            raise RuntimeError(
                f"{archive_path}!{member_name}:{line_no}: "
                f"columns={len(values)} expected={len(schema)}"
            )
        if not any(values):
            raise RuntimeError(
                f"{archive_path}!{member_name}:{line_no}: unexpected blank row"
            )
        rows.append(dict(zip(schema, values)))

    return rows


def _validate_rows(
    code: str,
    cfg: dict[str, Any],
    rows: list[dict[str, str]],
) -> None:
    if not rows:
        raise RuntimeError(f"{code}: no data rows")

    expected_code6 = cfg["code6"]
    seen_ids: set[str] = set()

    for line_no, row in enumerate(rows, start=2):
        actual_code6 = row["全国地方公共団体コード"]
        if actual_code6 != expected_code6:
            raise RuntimeError(
                f"{code}:{line_no}: municipality code={actual_code6!r} "
                f"expected={expected_code6!r}"
            )

        row_id = row["ID"]
        if not row_id:
            raise RuntimeError(f"{code}:{line_no}: blank ID")
        if row_id in seen_ids:
            raise RuntimeError(f"{code}:{line_no}: duplicate ID={row_id!r}")
        seen_ids.add(row_id)


def _prepare_one(
    code: str,
    cfg: dict[str, Any],
    schema: list[str],
) -> tuple[Path, Path, list[dict[str, str]]]:
    raw_dir = RAW / cfg["prefecture_dir"] / cfg["municipality_dir"] / "public-toilet"
    archive_path = raw_dir / cfg["archive"]
    destination = (
        OUT
        / cfg["prefecture_dir"]
        / cfg["municipality_dir"]
        / "public-toilet"
        / "public-toilet.csv"
    )

    if destination.exists():
        raise RuntimeError(f"{code}: output exists: {destination}")

    rows = _read_archive_member(archive_path, cfg["member"], schema)
    _validate_rows(code, cfg, rows)

    patches = common.load_patches(
        cfg["prefecture_dir"], cfg["municipality_dir"]
    )
    applied, problems = common.apply_patches(rows, patches, archive_path)
    if problems:
        raise RuntimeError("\n".join(problems))

    return archive_path, destination, rows, applied


def main() -> None:
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    prepared = []
    for code, cfg in TARGETS.items():
        archive_path, destination, rows, applied = _prepare_one(code, cfg, schema)
        prepared.append((code, cfg, archive_path, destination, rows, applied))

    print(f"preflight OK: {len(prepared)} municipalities")

    for code, cfg, archive_path, destination, rows, applied in prepared:
        StandardCsvWriter().write(destination, schema, rows)
        print(
            f"OK {code} {cfg['municipality_dir']}: "
            f"rows={len(rows)} source={archive_path.name}!{cfg['member']} "
            f"format=utf-8-sig patches={applied}"
        )


if __name__ == "__main__":
    main()
