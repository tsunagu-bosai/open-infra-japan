#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "03"
PREFECTURE_NAME = "岩手県"
HANDLERS = [
    # 03201 盛岡市, 03202 宮古市, 03215 奥州市
    Handler("legacy32_standard", ('03201', '03202', '03215')),
    # 03207 久慈市
    Handler("standard_superset", ('03207',)),
    # 03209 一関市
    Handler("ichinoseki", ('03209',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
