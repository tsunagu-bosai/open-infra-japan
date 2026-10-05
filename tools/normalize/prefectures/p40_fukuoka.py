#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "40"
PREFECTURE_NAME = "福岡県"
HANDLERS = [
    # 40100 北九州市
    Handler("kitakyushu", ('40100',)),
    # 40218 春日市
    Handler("legacy32_standard", ('40218',)),
    # 40203 久留米市
    Handler("tama_shinshiro_kumano_kurume_taku", ('40203',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
