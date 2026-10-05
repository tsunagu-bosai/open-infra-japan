#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "07"
PREFECTURE_NAME = "福島県"
HANDLERS = [
    # 07201 福島市, 07203 郡山市
    Handler("simple_location", ('07201', '07203')),
    # 07202 会津若松市
    Handler("aizu_machida", ('07202',)),
    # 07207 須賀川市
    Handler("legacy32_standard", ('07207',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
