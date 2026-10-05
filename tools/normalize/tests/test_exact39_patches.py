from __future__ import annotations

import unittest
from pathlib import Path

from tools.normalize_public_toilet import (
    apply_patches,
    normalize_publisher_municipality_code,
)


class ApplyPatchesTest(unittest.TestCase):
    def test_existing_id_selector_remains_supported(self) -> None:
        rows = [{"ID": "A1", "名称": "施設A", "備考": "old"}]
        patches = [{
            "id": "A1",
            "field": "備考",
            "original_value": "old",
            "patched_value": "new",
        }]

        applied, problems = apply_patches(rows, patches, Path("source.csv"))

        self.assertEqual(applied, 1)
        self.assertEqual(problems, [])
        self.assertEqual(rows[0]["備考"], "new")

    def test_explicit_selector_supports_blank_id_rows(self) -> None:
        rows = [
            {"ID": "", "名称": "高洲境川沿い緑道", "全国地方公共団体コード": "122270"},
            {"ID": "", "名称": "別施設", "全国地方公共団体コード": "122271"},
        ]
        patches = [{
            "match_field": "名称",
            "match_value": "高洲境川沿い緑道",
            "field": "全国地方公共団体コード",
            "original_value": "122270",
            "patched_value": "122271",
        }]

        applied, problems = apply_patches(rows, patches, Path("source.xlsx"))

        self.assertEqual(applied, 1)
        self.assertEqual(problems, [])
        self.assertEqual(rows[0]["全国地方公共団体コード"], "122271")
        self.assertEqual(rows[1]["全国地方公共団体コード"], "122271")

    def test_explicit_selector_must_be_unique(self) -> None:
        rows = [
            {"ID": "", "名称": "重複", "全国地方公共団体コード": "1"},
            {"ID": "", "名称": "重複", "全国地方公共団体コード": "1"},
        ]
        patches = [{
            "match_field": "名称",
            "match_value": "重複",
            "field": "全国地方公共団体コード",
            "original_value": "1",
            "patched_value": "2",
        }]

        applied, problems = apply_patches(rows, patches, Path("source.xlsx"))

        self.assertEqual(applied, 0)
        self.assertEqual(len(problems), 1)
        self.assertIn("expected 1 row, found 2", problems[0])


class PublisherMunicipalityCodeTest(unittest.TestCase):
    def test_normalizes_dropped_leading_zero_only_for_publisher_code(self) -> None:
        row = {
            "全国地方公共団体コード": "12301",
            "所在地_全国地方公共団体コード": "",
            "備考": "",
        }

        normalize_publisher_municipality_code(row, "01230-登別市")

        self.assertEqual(row["全国地方公共団体コード"], "012301")
        self.assertEqual(row["所在地_全国地方公共団体コード"], "")
        self.assertEqual(row["備考"], "原データ全国地方公共団体コード=12301")

    def test_location_code_is_not_forced_to_match_publisher(self) -> None:
        row = {
            "全国地方公共団体コード": "132110",
            "所在地_全国地方公共団体コード": "132012",
            "備考": "",
        }

        normalize_publisher_municipality_code(row, "13211-小平市")

        self.assertEqual(row["全国地方公共団体コード"], "132110")
        self.assertEqual(row["所在地_全国地方公共団体コード"], "132012")

    def test_rejects_wrong_publisher_code_after_source_patches(self) -> None:
        row = {
            "全国地方公共団体コード": "122270",
            "所在地_全国地方公共団体コード": "",
            "備考": "",
        }

        with self.assertRaises(RuntimeError):
            normalize_publisher_municipality_code(row, "12227-浦安市")


if __name__ == "__main__":
    unittest.main()
