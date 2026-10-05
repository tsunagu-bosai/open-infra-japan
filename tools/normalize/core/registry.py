from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class Handler:
    module: str
    codes: tuple[str, ...] = ()
    managed_codes: tuple[str, ...] = ()
    exact39_exclude_codes: tuple[str, ...] = ()
