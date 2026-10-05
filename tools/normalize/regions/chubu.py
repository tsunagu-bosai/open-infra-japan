#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.runner import region_cli

REGION_NAME = '中部地方'
PREFECTURE_MODULES = ['tools.normalize.prefectures.p15_niigata', 'tools.normalize.prefectures.p16_toyama', 'tools.normalize.prefectures.p17_ishikawa', 'tools.normalize.prefectures.p18_fukui', 'tools.normalize.prefectures.p19_yamanashi', 'tools.normalize.prefectures.p20_nagano', 'tools.normalize.prefectures.p21_gifu', 'tools.normalize.prefectures.p22_shizuoka', 'tools.normalize.prefectures.p23_aichi']


def main() -> int:
    return region_cli(REGION_NAME, PREFECTURE_MODULES)


if __name__ == "__main__":
    raise SystemExit(main())
