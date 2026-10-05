#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "24"
PREFECTURE_NAME = "三重県"
HANDLERS = [
    # 24207 鈴鹿市
    Handler("suzuka", ('24207',)),
    # 24212 熊野市
    Handler("tama_shinshiro_kumano_kurume_taku", ('24212',)),
    # 24202 四日市市
    Handler("manazuru_nagano_yokkaichi", ('24202',)),
    # 24210 亀山市, 24324 東員町
    Handler("standard_superset", ('24210', '24324')),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
