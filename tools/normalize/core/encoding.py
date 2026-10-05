from __future__ import annotations

from pathlib import Path


DEFAULT_ENCODINGS = ("utf-8-sig", "utf-8", "cp932", "shift_jis")


def detect_text_encoding(
    path: Path,
    encodings: tuple[str, ...] = DEFAULT_ENCODINGS,
) -> str:
    """Return the first encoding that can decode the complete file."""
    raw = path.read_bytes()
    for encoding in encodings:
        try:
            raw.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"cannot decode: {path}")
