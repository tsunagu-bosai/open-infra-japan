#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "06"
PREFECTURE_NAME = "山形県"
HANDLERS = [
    # 山形県共通10列形式
    Handler("yamagata_simple10", (
        '06201',
        '06202',
        '06203',
        '06204',
        '06205',
        '06206',
        '06207',
        '06208',
        '06209',
        '06211',
        '06212',
        '06213',
        '06302',
        '06321',
        '06322',
        '06323',
        '06324',
        '06362',
        '06365',
        '06402',
        '06461',
    )),
    # 06363 舟形町
    Handler("yamagata_funagata", ('06363',)),
    # 06210 天童市
    Handler("yamagata_tendo", ('06210',)),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
