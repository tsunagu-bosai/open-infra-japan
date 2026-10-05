#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "08"
PREFECTURE_NAME = "茨城県"
HANDLERS = [
    # 08205 石岡市, 08235 つくばみらい市
    Handler("legacy32_standard", ('08205', '08235')),
    # 08233 行方市
    Handler("noshiro_namegata_meguro", ('08233',)),
    # 08202 日立市
    Handler("hitachi_shibuya_nakano_sabae", ('08202',)),
    # 08216 笠間市
    Handler("kasama_gosen_miyoshi_tamba_otoyo_genkai_tamana_nagomi", ('08216',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
