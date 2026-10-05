#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "18"
PREFECTURE_NAME = "福井県"
HANDLERS = [
    # 18382 池田町
    Handler("fukui_ikeda", ('18382',)),
    # 18204 小浜市, 18205 大野市, 18208 あわら市, 18209 越前市, 18210 坂井市, 18322 永平寺町
    Handler("fukui_english39_special", ('18204', '18205', '18208', '18209', '18210', '18322')),
    # 18201 福井市, 18202 敦賀市, 18206 勝山市, 18404 南越前町, 18423 越前町, 18442 美浜町, 18481 高浜町, 18483 おおい町, 18501 若狭町
    Handler("fukui_english39_standard", ('18201', '18202', '18206', '18404', '18423', '18442', '18481', '18483', '18501')),
    # 18207 鯖江市
    Handler("hitachi_shibuya_nakano_sabae", ('18207',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
