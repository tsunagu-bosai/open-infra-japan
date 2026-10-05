#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "39"
PREFECTURE_NAME = "高知県"
HANDLERS = [
    # 39206 須崎市
    # 39208 宿毛市
    # 39210 四万十市
    Handler("legacy32_reviewed", ("39206", "39208", "39210")),

    # 39205 土佐市
    Handler("simple_location", ("39205",)),

    # 39344 大豊町
    Handler(
        "kasama_gosen_miyoshi_tamba_otoyo_genkai_tamana_nagomi",
        ("39344",),
    ),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
