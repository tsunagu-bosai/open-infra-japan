#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.runner import region_cli

REGION_NAME = '東北地方'
PREFECTURE_MODULES = ['tools.normalize.prefectures.p02_aomori', 'tools.normalize.prefectures.p03_iwate', 'tools.normalize.prefectures.p04_miyagi', 'tools.normalize.prefectures.p05_akita', 'tools.normalize.prefectures.p06_yamagata', 'tools.normalize.prefectures.p07_fukushima']


def main() -> int:
    return region_cli(REGION_NAME, PREFECTURE_MODULES)


if __name__ == "__main__":
    raise SystemExit(main())
