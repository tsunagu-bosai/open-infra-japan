#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "14"
PREFECTURE_NAME = "神奈川県"
HANDLERS = [
    # 14201 横須賀市
    Handler("kanagawa", ('14201',)),
    # 14204 鎌倉市
    Handler("kamakura", ('14204',)),
    # 14207 茅ヶ崎市, 14362 大井町
    Handler("legacy32_standard", ('14207', '14362')),
    # 14208 逗子市
    Handler("simple_location", ('14208',)),
    # 14211 秦野市
    Handler("nearstandard", ('14211',)),
    # 14212 厚木市
    Handler("atsugi", ('14212',)),
    # 14301 葉山町
    Handler("hayama", ('14301',)),
    # 14383 真鶴町
    Handler("manazuru_nagano_yokkaichi", ('14383',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
