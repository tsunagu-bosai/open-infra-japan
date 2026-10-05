#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "43"
PREFECTURE_NAME = "熊本県"
HANDLERS = [
    # 43403 大津町
    Handler("simple_location", ('43403',)),
    # 43216 合志市
    Handler("koshi", ('43216',)),
    # 43428 高森町
    Handler("kumamoto_takamori", ('43428',)),
    # 43348 美里町
    Handler("legacy32_standard", ('43348',)),
    # 43215 天草市, 43433 南阿蘇村
    Handler("nearstandard", ('43215', '43433')),
    # 43206 玉名市, 43369 和水町
    Handler("kasama_gosen_miyoshi_tamba_otoyo_genkai_tamana_nagomi", ('43206', '43369')),
    # 43468 氷川町
    Handler("standard_superset", ('43468',)),
    # 43213 宇城市
    Handler("uki_taketomi", ('43213',)),
    # 43505 多良木町
    Handler("taragi", ('43505',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
