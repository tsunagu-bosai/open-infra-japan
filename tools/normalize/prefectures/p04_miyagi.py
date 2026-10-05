#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "04"
PREFECTURE_NAME = "宮城県"
HANDLERS = [
    # 04212 登米市
    Handler("legacy32_standard", ('04212',)),
    # 04202 石巻市, 04203 塩竈市, 04206 白石市, 04207 名取市, 04209 多賀城市, 04213 栗原市, 04214 東松島市, 04322 村田町, 04323 柴田町, 04361 亘理町, 04401 松島町, 04421 大和町, 04501 涌谷町
    Handler("miyagi", ('04202', '04203', '04206', '04207', '04209', '04213', '04214', '04322', '04323', '04361', '04401', '04421', '04501')),
    # 04100 仙台市
    Handler("standard_superset", ('04100',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
