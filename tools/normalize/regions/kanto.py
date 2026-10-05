#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.runner import region_cli

REGION_NAME = '関東地方'
PREFECTURE_MODULES = ['tools.normalize.prefectures.p08_ibaraki', 'tools.normalize.prefectures.p09_tochigi', 'tools.normalize.prefectures.p10_gunma', 'tools.normalize.prefectures.p11_saitama', 'tools.normalize.prefectures.p12_chiba', 'tools.normalize.prefectures.p13_tokyo', 'tools.normalize.prefectures.p14_kanagawa']


def main() -> int:
    return region_cli(REGION_NAME, PREFECTURE_MODULES)


if __name__ == "__main__":
    raise SystemExit(main())
