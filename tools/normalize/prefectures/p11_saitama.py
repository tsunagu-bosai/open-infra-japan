#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "11"
PREFECTURE_NAME = "埼玉県"
HANDLERS = [
    # 11202 熊谷市
    Handler("kumagaya", ('11202',)),
    # 11201 川越市, 11211 本庄市
    Handler("alias_variants", ('11201', '11211')),
    # 11203 川口市, 11225 入間市
    Handler("standard_superset", ('11203', '11225')),
    # 11230 新座市
    Handler("legacy32_standard", ('11230',)),
    # 11210 加須市, 11219 上尾市
    Handler("saitama_remaining", ('11210', '11219')),
    # 11239 坂戸市
    Handler("sakado_otsu", ('11239',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
