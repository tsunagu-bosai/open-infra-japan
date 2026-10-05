from __future__ import annotations

import re


_CHECK_DIGIT_WEIGHTS = (6, 5, 4, 3, 2)


def six_digit_municipality_code(code5: str) -> str:
    """Convert a 5-digit municipality code to its 6-digit checked form."""
    if not re.fullmatch(r"\d{5}", code5):
        raise RuntimeError(
            f"invalid 5-digit municipality code: {code5!r}"
        )

    remainder = sum(
        int(digit) * weight
        for digit, weight in zip(code5, _CHECK_DIGIT_WEIGHTS)
    ) % 11
    check_digit = (11 - remainder) % 10
    return f"{code5}{check_digit}"
