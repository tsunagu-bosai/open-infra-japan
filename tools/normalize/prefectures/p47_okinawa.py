#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "47"
PREFECTURE_NAME = "沖縄県"
HANDLERS = [
    # 47211 沖縄市
    Handler("alias_variants", ('47211',)),
    # 47327 北中城村
    Handler("legacy32_reviewed", ('47327',)),
    # 47201 那覇市, 47302 大宜味村, 47357 南大東村
    Handler("legacy32_standard", ('47201', '47302', '47357')),
    # 47350 南風原町
    Handler("standard_superset", ('47350',)),
    # 47381 竹富町
    Handler("uki_taketomi", ('47381',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
