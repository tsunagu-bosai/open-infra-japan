#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "13"
PREFECTURE_NAME = "東京都"
HANDLERS = [
    # 13103 港区
    Handler("minato", ('13103',)),
    # 13105 文京区
    Handler("bunkyo", ('13105',)),
    # 13209 町田市
    Handler("aizu_machida", ('13209',)),
    # 13308 奥多摩町
    Handler("alias_variants", ('13308',)),
    # 13116 豊島区, 13221 清瀬市
    Handler("legacy32_standard", ('13116', '13221')),
    # 13110 目黒区
    Handler("noshiro_namegata_meguro", ('13110',)),
    # 13224 多摩市
    Handler("tama_shinshiro_kumano_kurume_taku", ('13224',)),
    # 13228 あきる野市
    Handler("hakodate_aomori_daisen_akiruno", ('13228',)),
    # 13113 渋谷区, 13114 中野区
    Handler("hitachi_shibuya_nakano_sabae", ('13113', '13114')),
    # 13218 福生市
    Handler("chippubetsu_fussa_matsuyama", ('13218',)),
    # 13109 品川区
    Handler("shinagawa", ('13109',)),
    # 13229 西東京市, 13201 八王子市, 13225 稲城市
    Handler("standard_superset", ('13229', '13201', '13225')),
    # 13117 北区
    Handler("archive_standard", ('13117',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
