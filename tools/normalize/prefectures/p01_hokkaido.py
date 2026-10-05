#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "01"
PREFECTURE_NAME = "北海道"
HANDLERS = [
    # 01231 恵庭市, 01304 新篠津村, 01425 上砂川町, 01465 剣淵町, 01604 新冠町, 01647 足寄町, 01691 別海町
    Handler(
        "legacy32_standard",
        ('01231', '01304', '01425', '01465', '01604', '01647', '01691'),
    ),
    # 01211 網走市
    Handler("legacy26_standard", ('01211',)),
    # 01202 函館市
    Handler("hakodate_aomori_daisen_akiruno", ('01202',)),
    # 01229 富良野市
    Handler("furano_oga_sanjo_oyabe_sakai", ('01229',)),
    # 01434 秩父別町
    Handler("chippubetsu_fussa_matsuyama", ('01434',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
