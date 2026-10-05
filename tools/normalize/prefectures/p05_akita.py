#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "05"
PREFECTURE_NAME = "秋田県"
HANDLERS = [
    # 05209 鹿角市
    Handler("standard_superset", ('05209',)),
    # 05202 能代市
    Handler("noshiro_namegata_meguro", ('05202',)),
    # 05212 大仙市
    Handler("hakodate_aomori_daisen_akiruno", ('05212',)),
    # 05206 男鹿市
    Handler("furano_oga_sanjo_oyabe_sakai", ('05206',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
