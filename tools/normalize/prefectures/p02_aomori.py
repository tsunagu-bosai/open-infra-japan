#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "02"
PREFECTURE_NAME = "青森県"
HANDLERS = [
    # 02210 平川市
    Handler("hirakawa_namerikawa", ('02210',)),
    # 02201 青森市
    Handler("hakodate_aomori_daisen_akiruno", ('02201',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
