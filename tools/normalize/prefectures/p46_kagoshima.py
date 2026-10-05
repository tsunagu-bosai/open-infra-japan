#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "46"
PREFECTURE_NAME = "鹿児島県"
HANDLERS = [
    # 46201 鹿児島市
    Handler("simple_location", ('46201',)),
    # 46221 志布志市
    Handler("alias_variants", ('46221',)),
    # 46214 垂水市, 46223 南九州市, 46225 姶良市, 46492 肝付町, 46502 南種子町
    Handler("legacy32_standard", ('46214', '46223', '46225', '46492', '46502', '46535')),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
