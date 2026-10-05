from __future__ import annotations

from pathlib import Path

import xlrd


class LinkDataXlsReader:
    """Reader for LinkData.org legacy XLS workbooks."""

    PROPERTY_MARKER = "#property"
    PROPERTY_CONTEXT_MARKER = "#property_context"

    @staticmethod
    def _cell_text(value) -> str:
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return "" if value is None else str(value).strip()

    def read(self, path: Path) -> list[dict[str, str]]:
        book = xlrd.open_workbook(path)
        sheet = book.sheet_by_index(0)

        property_row = None
        context_row = None

        for row_index in range(sheet.nrows):
            first = self._cell_text(sheet.cell_value(row_index, 0))

            if first == self.PROPERTY_MARKER:
                if property_row is not None:
                    raise RuntimeError(
                        f"{path}: duplicate {self.PROPERTY_MARKER} row"
                    )
                property_row = row_index

            elif first == self.PROPERTY_CONTEXT_MARKER:
                if context_row is not None:
                    raise RuntimeError(
                        f"{path}: duplicate {self.PROPERTY_CONTEXT_MARKER} row"
                    )
                context_row = row_index

        if property_row is None:
            raise RuntimeError(f"{path}: {self.PROPERTY_MARKER} row not found")

        if context_row is None:
            raise RuntimeError(
                f"{path}: {self.PROPERTY_CONTEXT_MARKER} row not found"
            )

        if context_row <= property_row:
            raise RuntimeError(
                f"{path}: invalid LinkData metadata row order"
            )

        header = [
            self._cell_text(sheet.cell_value(property_row, column))
            for column in range(sheet.ncols)
        ]

        rows: list[dict[str, str]] = []

        for row_index in range(context_row + 1, sheet.nrows):
            values = [
                self._cell_text(sheet.cell_value(row_index, column))
                for column in range(sheet.ncols)
            ]

            if not any(values):
                continue

            rows.append(
                {
                    header[column]: values[column]
                    for column in range(len(header))
                    if header[column]
                }
            )

        if not rows:
            raise RuntimeError(f"{path}: LinkData workbook has no data rows")

        return rows
