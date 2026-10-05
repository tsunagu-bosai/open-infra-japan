#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "27"
PREFECTURE_NAME = "大阪府"
HANDLERS = [
    # 27100 大阪市
    Handler("osaka_city", ('27100',)),
    # 27216 河内長野市
    Handler("kawachinagano", ('27216',)),
    # 27210 枚方市
    Handler("hirakata", ('27210',)),
    # 27215 寝屋川市
    Handler("legacy32_reviewed", ('27215',)),
    # 27208 貝塚市, 27209 守口市, 27223 門真市, 27232 阪南市
    Handler("legacy32_standard", ('27208', '27209', '27223', '27232')),
    # 27361 熊取町
    Handler("nearstandard", ('27361',)),
    # 27140 堺市
    Handler("furano_oga_sanjo_oyabe_sakai", ('27140',)),
    Handler(
        "osaka_prefecture",
        (),
        exact39_exclude_codes=("27000",),
    ),
    # 27203 豊中市
    Handler("standard_superset", ('27203',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
