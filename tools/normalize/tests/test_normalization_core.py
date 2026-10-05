from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from tools.normalize.core.normalization import (
    AllowedValueStrategy,
    CsvDictSourceReader,
    LenientEndOfDayTimeStrategy,
    LenientHmsTimeStrategy,
    LenientTwentyFourTimeStrategy,
    PreserveEndOfDayTimeStrategy,
    PreserveInvalidTimeStrategy,
    RowSupport,
    Sha256StableIdStrategy,
    StandardCsvWriter,
    StrictEndOfDayTimeStrategy,
    StrictHmTimeStrategy,
    StrictHmsTimeStrategy,
    ValueCleaner,
)


class NormalizationCoreTest(unittest.TestCase):
    def test_clean_cell_normalizes_integer_float(self) -> None:
        self.assertEqual(RowSupport.clean_cell(12.0), "12")
        self.assertEqual(RowSupport.clean_cell(12.5), "12.5")
        self.assertEqual(RowSupport.clean_cell(None), "")

    def test_value_cleaner_can_drop_or_preserve_placeholders(self) -> None:
        cleaner = ValueCleaner({"-", "なし"})
        self.assertEqual(cleaner(" - "), "")
        self.assertEqual(cleaner("なし", preserve_placeholder=True), "なし")
        self.assertEqual(cleaner("値"), "値")

    def test_allowed_value_strategy_uses_configured_cleaner(self) -> None:
        strategy = AllowedValueStrategy(("", "有", "無"), cleaner=RowSupport.clean_cell)
        self.assertEqual(strategy(" 有 ", "車椅子使用者用トイレ有無"), "有")
        self.assertEqual(strategy(None, "車椅子使用者用トイレ有無"), "")
        with self.assertRaisesRegex(RuntimeError, "unexpected value"):
            strategy("可", "車椅子使用者用トイレ有無")

    def test_append_note_is_idempotent(self) -> None:
        row = {"備考": "既存"}
        RowSupport.append_note(row, "追加")
        RowSupport.append_note(row, "追加")
        self.assertEqual(row["備考"], "既存 / 追加")

    def test_append_text_can_target_non_note_field(self) -> None:
        row = {"利用可能時間特記事項": "既存"}
        RowSupport.append_text(row, "利用可能時間特記事項", "追加")
        RowSupport.append_text(row, "利用可能時間特記事項", "追加")
        self.assertEqual(row["利用可能時間特記事項"], "既存 / 追加")

    def test_append_note_can_preserve_custom_separator(self) -> None:
        row = {"備考": "既存"}
        RowSupport.append_note(row, "追加", separator="; ")
        RowSupport.append_note(row, "追加", separator="; ")
        self.assertEqual(row["備考"], "既存; 追加")


    def test_strict_hms_time_strategy(self) -> None:
        strategy = StrictHmsTimeStrategy()
        self.assertEqual(strategy("9：05"), "09:05")
        self.assertEqual(strategy("09:05:00"), "09:05")
        with self.assertRaises(RuntimeError):
            strategy("09:05:01")

    def test_preserve_invalid_time_strategy(self) -> None:
        strategy = PreserveInvalidTimeStrategy()
        self.assertEqual(strategy("9:05"), ("09:05", None))
        self.assertEqual(strategy("24:00"), ("", "24:00"))
        self.assertEqual(strategy("不明"), ("", "不明"))

    def test_lenient_end_of_day_time_strategy(self) -> None:
        strategy = LenientEndOfDayTimeStrategy()
        self.assertEqual(strategy("24:00"), "23:59")
        self.assertEqual(strategy("9:05"), "09:05")
        self.assertEqual(strategy("終日"), "終日")

    def test_lenient_hms_time_strategy(self) -> None:
        strategy = LenientHmsTimeStrategy()
        self.assertEqual(strategy("9：05:00"), "09:05")
        self.assertEqual(strategy("24:00"), "24:00")
        self.assertEqual(strategy("終日"), "終日")

    def test_strict_end_of_day_time_strategy_preserves_source_note(self) -> None:
        strategy = StrictEndOfDayTimeStrategy()
        row = {"備考": ""}
        self.assertEqual(strategy("24:00", row, "利用終了時間"), "23:59")
        self.assertEqual(row["備考"], "原データ利用終了時間=24:00")

    def test_strict_hm_time_strategy(self) -> None:
        strategy = StrictHmTimeStrategy()
        self.assertEqual(strategy("9：05"), "09:05")
        with self.assertRaises(RuntimeError):
            strategy("09:05:00")

    def test_lenient_twenty_four_time_strategy(self) -> None:
        strategy = LenientTwentyFourTimeStrategy()
        self.assertEqual(strategy("9:05"), "09:05")
        self.assertEqual(strategy("24:00"), "24:00")
        self.assertEqual(strategy("24:01"), "24:01")
        self.assertEqual(strategy("終日"), "終日")

    def test_preserve_end_of_day_time_strategy(self) -> None:
        strategy = PreserveEndOfDayTimeStrategy()
        self.assertEqual(strategy("9：05:00"), ("09:05", None))
        self.assertEqual(strategy("24:00"), ("23:59", "24:00"))
        self.assertEqual(strategy("不明"), ("", "不明"))

    def test_stable_id_is_deterministic(self) -> None:
        strategy = Sha256StableIdStrategy()
        first = strategy.generate("14362", "農村公園", "住所", "", "", "")
        second = strategy.generate("14362", "農村公園", "住所", "", "", "")
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("14362-SRC-"))

    def test_stable_id_template_can_preserve_legacy_format(self) -> None:
        strategy = Sha256StableIdStrategy(template="{code}-{digest}")
        value = strategy.generate("14212", "固定式", "1", "中央公園")
        self.assertEqual(value, "14212-148698B35D56AB18")

    def test_default_stable_id_format_is_unchanged(self) -> None:
        strategy = Sha256StableIdStrategy()
        value = strategy.generate("14362", "農村公園", "住所", "", "", "")
        self.assertEqual(value, "14362-SRC-DA3B2A561EB5DE2A")

    def test_append_labeled_note(self) -> None:
        row = {"備考": ""}
        RowSupport.append_labeled_note(row, "原データ区分", "固定式")
        self.assertEqual(row["備考"], "原データ区分=固定式")

    def test_csv_reader_filters_completely_blank_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "source.csv"
            path.write_text("名称,住所\n公園,住所1\n,\n,\n", encoding="utf-8")
            table = CsvDictSourceReader().read(path)
            self.assertEqual(table.header, ["名称", "住所"])
            self.assertEqual(len(table.rows), 1)
            self.assertEqual(table.rows[0]["名称"], "公園")

    def test_writer_writes_schema_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.csv"
            StandardCsvWriter().write(path, ["A", "B"], [{"A": "1", "B": "2"}])
            with path.open(encoding="utf-8-sig", newline="") as f:
                self.assertEqual(list(csv.reader(f)), [["A", "B"], ["1", "2"]])

    def test_stable_id_can_exclude_code_from_hash_material(self) -> None:
        strategy = Sha256StableIdStrategy(
            digest_length=12,
            include_code_in_material=False,
        )
        actual = strategy.generate("21202", "name", "address")

        import hashlib
        digest = hashlib.sha256("name|address".encode("utf-8")).hexdigest()[:12].upper()
        self.assertEqual(actual, f"21202-SRC-{digest}")


if __name__ == "__main__":
    unittest.main()
