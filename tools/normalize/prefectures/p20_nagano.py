#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "20"
PREFECTURE_NAME = "長野県"
HANDLERS = [
    # 20202 松本市, 20203 上田市, 20205 飯田市, 20207 須坂市
    Handler("nagano_custom", ('20202', '20203', '20205', '20207')),
    # 20214 茅野市, 20403 高森町
    Handler("legacy32_standard", ('20214', '20403')),
    # 20201 長野市
    Handler("manazuru_nagano_yokkaichi", ('20201',)),
    # 20321 軽井沢町
    Handler("karuizawa_uda_kainan_hiroshima", ('20321',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
