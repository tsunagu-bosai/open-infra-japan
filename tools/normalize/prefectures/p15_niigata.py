#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "15"
PREFECTURE_NAME = "新潟県"
HANDLERS = [
    # 15204 三条市
    Handler("furano_oga_sanjo_oyabe_sakai", ('15204',)),
    # 15218 五泉市
    Handler("kasama_gosen_miyoshi_tamba_otoyo_genkai_tamana_nagomi", ('15218',)),
    # 15212 村上市
    Handler("standard_superset", ('15212',)),
    # 15225 魚沼市
    Handler("uonuma", ('15225',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
