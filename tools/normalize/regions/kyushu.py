#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.runner import region_cli

REGION_NAME = '九州地方'
PREFECTURE_MODULES = ['tools.normalize.prefectures.p40_fukuoka', 'tools.normalize.prefectures.p41_saga', 'tools.normalize.prefectures.p42_nagasaki', 'tools.normalize.prefectures.p43_kumamoto', 'tools.normalize.prefectures.p44_oita', 'tools.normalize.prefectures.p45_miyazaki', 'tools.normalize.prefectures.p46_kagoshima', 'tools.normalize.prefectures.p47_okinawa']


def main() -> int:
    return region_cli(REGION_NAME, PREFECTURE_MODULES)


if __name__ == "__main__":
    raise SystemExit(main())
