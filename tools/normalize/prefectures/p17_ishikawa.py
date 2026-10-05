#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "17"
PREFECTURE_NAME = "石川県"
HANDLERS = [
    # 17361 津幡町
    Handler("alias_variants", ('17361',)),
    # 17202 七尾市, 17206 加賀市, 17207 羽咋市, 17407 中能登町
    Handler("legacy32_standard", ('17202', '17206', '17207', '17407')),
    # 17201 金沢市, 17209 かほく市, 17210 白山市, 17212 野々市市,
    # 17365 内灘町, 17463 能登町
    Handler("standard_superset", ('17201', '17209', '17210', '17212', '17365', '17463')),
    # 17203 小松市, 17204 輪島市, 17205 珠洲市, 17324 川北町,
    # 17384 志賀町, 17386 宝達志水町, 17461 穴水町
    Handler(
        "ishikawa_variants",
        ("17203", "17204", "17205", "17324", "17384", "17386", "17461"),
    ),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
