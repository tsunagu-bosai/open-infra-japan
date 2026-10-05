from __future__ import annotations

import unittest

from tools.normalize.core.municipality import six_digit_municipality_code


class SixDigitMunicipalityCodeTest(unittest.TestCase):
    def test_known_official_codes(self) -> None:
        cases = {
            "01211": "012114",  # 網走市
            "01230": "012301",  # 登別市
            "01231": "012319",  # 恵庭市
            "01647": "016471",  # 足寄町
            "11210": "112101",  # 加須市
        }

        for code5, expected in cases.items():
            with self.subTest(code5=code5):
                self.assertEqual(
                    six_digit_municipality_code(code5),
                    expected,
                )

    def test_modulus_11_boundary_cases(self) -> None:
        # 総務省/J-LIS仕様:
        # 余り0 -> 1
        # 余り1 -> 0
        # 余り10 -> 1
        cases = {
            "00014": "000141",
            "00023": "000230",
            "00019": "000191",
        }

        for code5, expected in cases.items():
            with self.subTest(code5=code5):
                self.assertEqual(
                    six_digit_municipality_code(code5),
                    expected,
                )

    def test_rejects_invalid_five_digit_code(self) -> None:
        for value in ("1234", "123456", "12A30", ""):
            with self.subTest(value=value):
                with self.assertRaises(RuntimeError):
                    six_digit_municipality_code(value)


if __name__ == "__main__":
    unittest.main()
