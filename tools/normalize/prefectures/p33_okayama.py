#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "33"
PREFECTURE_NAME = "岡山県"
HANDLERS = [
    # 33100 岡山市
    Handler("okayama_city", ("33100",)),

    # 33681 吉備中央町
    # 公式39列だが、真偽値が0/1表現のため専用正規化。
    # exact39共通処理との二重生成を防ぐ。
    Handler(
        "kibichuo",
        ("33681",),
        exact39_exclude_codes=("33681",),
    ),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
