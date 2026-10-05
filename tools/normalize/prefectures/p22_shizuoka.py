#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "22"
PREFECTURE_NAME = "静岡県"
HANDLERS = [
    Handler("shizuoka", ('22100', '22203', '22206', '22207', '22208', '22209', '22211', '22212', '22213', '22214', '22215', '22216', '22219', '22220', '22222', '22223', '22224', '22225', '22226', '22301', '22302', '22305', '22306', '22341')),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
