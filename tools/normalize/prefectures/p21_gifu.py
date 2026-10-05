#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "21"
PREFECTURE_NAME = "岐阜県"
HANDLERS = [
    # 21208 瑞浪市
    Handler("gifu_remaining", ('21208',)),
    # 21202 大垣市
    Handler("gifu_custom", ('21202',)),
    # 21209 羽島市
    Handler("gifu", ('21209',)),
    # 21203 高山市
    Handler("legacy32_standard", ('21203',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
