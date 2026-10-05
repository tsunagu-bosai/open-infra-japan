from __future__ import annotations

import csv
from pathlib import Path


def read_schema_fields(path: Path) -> list[str]:
    """Read ordered field names from a standard schema CSV."""
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        fields = [row["name"] for row in csv.DictReader(f)]

    if not fields:
        raise RuntimeError(f"schema has no fields: {path}")

    return fields
