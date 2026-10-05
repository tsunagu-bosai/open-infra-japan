#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "38"
PREFECTURE_NAME = "愛媛県"
HANDLERS = [
    # 38402 砥部町
    Handler("legacy32_standard", ('38402',)),
    # 38201 松山市
    Handler("chippubetsu_fussa_matsuyama", ('38201',)),
    # 38215 東温市
    Handler("legacy32_standard", ("38215",)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
