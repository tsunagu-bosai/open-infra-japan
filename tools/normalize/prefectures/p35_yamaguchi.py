#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "35"
PREFECTURE_NAME = "山口県"
HANDLERS = [
    # 35202 宇部市, 35206 防府市, 35207 下松市, 35212 柳井市, 35213 美祢市, 35215 周南市, 35305 周防大島町, 35343 田布施町
    Handler("yamaguchi", ('35202', '35206', '35207', '35212', '35213', '35215', '35305', '35343')),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
