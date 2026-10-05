#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "26"
PREFECTURE_NAME = "京都府"
HANDLERS = [
    # 26204 宇治市
    Handler("legacy32_reviewed", ('26204',)),
    # 26201 福知山市
    Handler("legacy32_standard", ('26201',)),
    # 26100 京都市
    Handler("kyoto", ('26100',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
