#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "36"
PREFECTURE_NAME = "徳島県"
HANDLERS = [
    # 36202 鳴門市
    # 36387 美波町
    Handler("legacy32_standard", ("36202", "36387")),

    # 36201 徳島市
    # 36203 小松島市
    # 36204 阿南市
    # 36205 吉野川市
    # 36206 阿波市
    # 36207 美馬市
    # 36208 三好市
    # 36301 勝浦町
    # 36302 上勝町
    # 36321 佐那河内村
    # 36341 石井町
    # 36342 神山町
    # 36368 那賀町
    # 36383 牟岐町
    # 36388 海陽町
    # 36401 松茂町
    # 36402 北島町
    # 36403 藍住町
    # 36404 板野町
    # 36405 上板町
    # 36468 つるぎ町
    # 36489 東みよし町
    #
    # 県統合「利用可能なトイレ一覧表」。
    # 鳴門市・美波町は既存の自治体別データを優先するため、
    # tokushima_prefecture 側で出力対象外とする。
    Handler("tokushima_prefecture", ()),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
