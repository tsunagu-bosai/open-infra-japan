#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "19"
PREFECTURE_NAME = "山梨県"
HANDLERS = [
    # 19211 笛吹市, 19365 身延町
    Handler("yamanashi_remaining", ('19211', '19365')),
    # 19425 山中湖村
    Handler("yamanashi_custom", ('19425',)),
    # 19209 北杜市
    Handler("nearstandard", ('19209',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
