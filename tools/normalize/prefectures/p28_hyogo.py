#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "28"
PREFECTURE_NAME = "兵庫県"
HANDLERS = [
    Handler("nearstandard", ("28501", "28586")),
    # 28100 神戸市
    Handler("kobe", ('28100',)),
    # 28204 西宮市
    Handler("legacy32_standard", ('28204',)),
    # 28208 相生市
    Handler("aioi", ('28208',)),
    # 28214 宝塚市
    Handler("takarazuka", ('28214',)),
    # 28229 たつの市
    Handler("alias_variants", ('28229',)),
    # 28223 丹波市
    Handler("kasama_gosen_miyoshi_tamba_otoyo_genkai_tamana_nagomi", ('28223',)),
    # 28585 香美町
    Handler("karuizawa_uda_kainan_hiroshima", ('28585',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
