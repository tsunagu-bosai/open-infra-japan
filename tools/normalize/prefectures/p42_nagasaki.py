#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "42"
PREFECTURE_NAME = "長崎県"
HANDLERS = [
    # 42202 佐世保市
    Handler("sasebo", ('42202',)),
    # 42203 島原市, 42308 時津町
    Handler("legacy32_standard", ('42203', '42308')),
    # 42209 対馬市, 42211 五島市, 42307 長与町
    Handler("standard_superset", ('42209', '42211', '42307')),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
