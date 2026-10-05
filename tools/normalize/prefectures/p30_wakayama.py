#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.normalize.core.registry import Handler
from tools.normalize.core.runner import prefecture_cli

PREFECTURE_CODE = "30"
PREFECTURE_NAME = "和歌山県"
HANDLERS = [
    # 30202 海南市
    Handler("karuizawa_uda_kainan_hiroshima", ('30202',)),
    Handler(
        "wakayama_prefecture",
        (),
        managed_codes=(
            "30203", "30204", "30205", "30206", "30207", "30208", "30209",
            "30341", "30343", "30344", "30361", "30362", "30366", "30381",
            "30382", "30383", "30390", "30391", "30392", "30401", "30404",
            "30406", "30421", "30422", "30424", "30427", "30428",
        ),
    ),
]

if __name__ == "__main__":
    raise SystemExit(prefecture_cli(PREFECTURE_CODE, PREFECTURE_NAME, HANDLERS))
