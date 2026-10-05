#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "09"
PREFECTURE_NAME = "栃木県"
HANDLERS = [
    # 09204 佐野市
    Handler("simple_location", ('09204',)),
    # 09214 さくら市
    Handler("legacy32_standard", ('09214',)),
    # 09201 宇都宮市
    Handler("standard_superset", ('09201',)),
    # 09208 小山市, 09211 矢板市
    Handler("tochigi", ('09208', '09211')),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
