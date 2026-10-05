#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.runner import region_cli

REGION_NAME = '近畿地方'
PREFECTURE_MODULES = ['tools.normalize.prefectures.p24_mie', 'tools.normalize.prefectures.p25_shiga', 'tools.normalize.prefectures.p26_kyoto', 'tools.normalize.prefectures.p27_osaka', 'tools.normalize.prefectures.p28_hyogo', 'tools.normalize.prefectures.p29_nara', 'tools.normalize.prefectures.p30_wakayama']


def main() -> int:
    return region_cli(REGION_NAME, PREFECTURE_MODULES)


if __name__ == "__main__":
    raise SystemExit(main())
