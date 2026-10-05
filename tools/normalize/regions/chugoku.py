#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.runner import region_cli

REGION_NAME = '中国地方'
PREFECTURE_MODULES = ['tools.normalize.prefectures.p31_tottori', 'tools.normalize.prefectures.p32_shimane', 'tools.normalize.prefectures.p33_okayama', 'tools.normalize.prefectures.p34_hiroshima', 'tools.normalize.prefectures.p35_yamaguchi']


def main() -> int:
    return region_cli(REGION_NAME, PREFECTURE_MODULES)


if __name__ == "__main__":
    raise SystemExit(main())
