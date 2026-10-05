#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "23"
PREFECTURE_NAME = "愛知県"
HANDLERS = [
    # 23100 名古屋市
    Handler("nagoya", ('23100',)),
    # 23203 一宮市, 23210 刈谷市, 23226 尾張旭市
    Handler("aichi_custom", ('23203', '23210', '23226')),
    # 23238 長久手市
    Handler("nagakute", ('23238',)),
    # 23207 豊川市
    Handler("legacy32_reviewed", ('23207',)),
    # 23209 碧南市, 23214 蒲郡市, 23215 犬山市, 23228 岩倉市, 23231 田原市
    Handler("legacy32_standard", ('23209', '23214', '23215', '23228', '23231')),
    # 23221 新城市
    Handler("tama_shinshiro_kumano_kurume_taku", ('23221',)),
    # 23211 豊田市
    Handler("nearstandard", ('23211',)),
    # 23229 豊明市
    Handler("toyoake_ikaruga", ('23229',)),
    # 23236 みよし市
    Handler("kasama_gosen_miyoshi_tamba_otoyo_genkai_tamana_nagomi", ('23236',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
