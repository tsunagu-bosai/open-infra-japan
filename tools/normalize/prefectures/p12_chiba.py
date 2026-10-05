#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "12"
PREFECTURE_NAME = "千葉県"
HANDLERS = [
    # 12202 銚子市, 12205 館山市, 12211 成田市, 12347 多古町
    Handler("chiba_standard_variants", ('12202', '12205', '12211', '12347')),
    # 12220 流山市, 12329 栄町
    Handler("legacy32_standard", ('12220', '12329')),
    # 12207 松戸市
    Handler("simple_location", ('12207',)),
    # 12221 八千代市
    Handler("yachiyo", ('12221',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
