#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "10"
PREFECTURE_NAME = "群馬県"
HANDLERS = [
    # 10421 中之条町
    Handler("alias_variants", ('10421',)),

    # 群馬県「オストメイト対応トイレ・
    # ユニバーサルシート設置状況一覧」。
    # 中之条町は既存の自治体別データを優先するため、
    # gunma_prefecture 側では出力対象外とする。
    Handler("gunma_prefecture", ()),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
