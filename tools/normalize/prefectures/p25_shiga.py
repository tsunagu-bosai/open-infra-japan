#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "25"
PREFECTURE_NAME = "滋賀県"
HANDLERS = [
    # 25202 彦根市, 25212 高島市
    Handler("legacy32_standard", ('25202', '25212')),
    # 25201 大津市
    Handler("sakado_otsu", ('25201',)),
    # 25204 近江八幡市
    Handler("standard_superset", ('25204',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
