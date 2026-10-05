#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "16"
PREFECTURE_NAME = "富山県"
HANDLERS = [
    # 16206 滑川市
    Handler("hirakawa_namerikawa", ('16206',)),
    # 16204 魚津市
    Handler("legacy32_standard", ('16204',)),
    # 16209 小矢部市
    Handler("furano_oga_sanjo_oyabe_sakai", ('16209',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
