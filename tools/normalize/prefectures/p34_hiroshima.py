#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "34"
PREFECTURE_NAME = "広島県"
HANDLERS = [
    Handler("kumano_direct", ("34307",)),
    # 34202 呉市, 34204 三原市, 34208 府中市, 34210 庄原市,
    # 34212 東広島市, 34304 海田町
    Handler(
        "hiroshima",
        ("34202", "34204", "34208", "34210", "34212", "34304"),
    ),
    # 34100 広島市
    Handler("karuizawa_uda_kainan_hiroshima", ("34100",)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
