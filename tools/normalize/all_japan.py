#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.runner import all_japan_cli

REGION_MODULES = [
    "tools.normalize.regions.hokkaido",
    "tools.normalize.regions.tohoku",
    "tools.normalize.regions.kanto",
    "tools.normalize.regions.chubu",
    "tools.normalize.regions.kinki",
    "tools.normalize.regions.chugoku",
    "tools.normalize.regions.shikoku",
    "tools.normalize.regions.kyushu",
]


def main() -> int:
    return all_japan_cli(REGION_MODULES)


if __name__ == "__main__":
    raise SystemExit(main())
