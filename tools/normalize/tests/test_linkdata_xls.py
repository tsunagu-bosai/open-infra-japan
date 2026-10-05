from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class FakeSheet:
    def __init__(self, rows):
        self._rows = rows
        self.nrows = len(rows)
        self.ncols = max((len(row) for row in rows), default=0)

    def cell_value(self, row_index, column_index):
        row = self._rows[row_index]
        if column_index >= len(row):
            return ""
        return row[column_index]


class FakeBook:
    def __init__(self, rows):
        self._sheet = FakeSheet(rows)

    def sheet_by_index(self, index):
        if index != 0:
            raise IndexError(index)
        return self._sheet


class LinkDataXlsReaderTest(unittest.TestCase):
    def _reader_for(self, rows):
        fake_xlrd = SimpleNamespace(
            open_workbook=lambda path: FakeBook(rows)
        )
        with patch.dict(sys.modules, {"xlrd": fake_xlrd}):
            sys.modules.pop(
                "tools.normalize.core.linkdata_xls",
                None,
            )
            module = importlib.import_module(
                "tools.normalize.core.linkdata_xls"
            )
        return module.LinkDataXlsReader()

    def test_reads_rows_after_property_context(self) -> None:
        reader = self._reader_for(
            [
                ["metadata"],
                ["#property", "住所", "数値"],
                [
                    "#property_context",
                    "xsd:string",
                    "xsd:integer",
                ],
                ["施設A", " 住所1 ", 12.0],
                ["", "", ""],
                ["施設B", "住所2", 12.5],
            ]
        )

        self.assertEqual(
            reader.read(Path("dummy.xls")),
            [
                {
                    "#property": "施設A",
                    "住所": "住所1",
                    "数値": "12",
                },
                {
                    "#property": "施設B",
                    "住所": "住所2",
                    "数値": "12.5",
                },
            ],
        )

    def test_missing_property_row_is_rejected(self) -> None:
        reader = self._reader_for(
            [["#property_context"], ["施設A"]]
        )
        with self.assertRaisesRegex(
            RuntimeError,
            "#property row not found",
        ):
            reader.read(Path("dummy.xls"))

    def test_duplicate_property_context_row_is_rejected(self) -> None:
        reader = self._reader_for(
            [
                ["#property", "住所"],
                ["#property_context", "xsd:string"],
                ["#property_context", "xsd:string"],
                ["施設A", "住所1"],
            ]
        )
        with self.assertRaisesRegex(
            RuntimeError,
            "duplicate #property_context row",
        ):
            reader.read(Path("dummy.xls"))

    def test_invalid_metadata_order_is_rejected(self) -> None:
        reader = self._reader_for(
            [
                ["#property_context", "xsd:string"],
                ["#property", "住所"],
                ["施設A", "住所1"],
            ]
        )
        with self.assertRaisesRegex(
            RuntimeError,
            "invalid LinkData metadata row order",
        ):
            reader.read(Path("dummy.xls"))

    def test_workbook_without_data_rows_is_rejected(self) -> None:
        reader = self._reader_for(
            [
                ["#property", "住所"],
                ["#property_context", "xsd:string"],
                ["", ""],
            ]
        )
        with self.assertRaisesRegex(
            RuntimeError,
            "LinkData workbook has no data rows",
        ):
            reader.read(Path("dummy.xls"))


if __name__ == "__main__":
    unittest.main()
