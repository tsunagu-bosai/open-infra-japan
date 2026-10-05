#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "29"
PREFECTURE_NAME = "奈良県"
HANDLERS = [
    Handler("nara_park", ('29201',)),
    Handler("nearstandard", ('29206', '29363', '29425')),
    # 29209 生駒市
    Handler("ikoma", ('29209',)),
    # 29205 橿原市
    Handler("alias_variants", ('29205',)),
    # 29203 大和郡山市
    Handler("legacy32_standard", ('29203', '29208', '29453')),
    # 29212 宇陀市
    Handler("karuizawa_uda_kainan_hiroshima", ('29212',)),
    # 29344 斑鳩町
    Handler("toyoake_ikaruga", ('29344',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
