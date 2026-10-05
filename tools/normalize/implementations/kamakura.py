#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.normalization import RowSupport, StandardCsvWriter
from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.xlsx import read_xlsx_values

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "14204": {
        "pref": "14-神奈川県",
        "mun": "14204-鎌倉市",
        "name": "神奈川県鎌倉市",
        "source": "toiletr80909.xlsx",
        "sheet": "★HP公開用20260901時点",
    },
}

EXPECTED_HEADER_ROWS = (
    ("Ｎｏ．", "施設名称", "所在地", "便器数", "", "", "", "", "", "", "", ""),
    ("", "", "", "合計", "男", "", "", "女", "", "多目的", "", ""),
    ("", "", "", "", "和", "洋", "小", "和", "洋", "身障", "オスト", "ベッド"),
)

EXPECTED_FOOTER_NOTES = (
    "※身障は、車いす対応",
    "※オストはオストメイト",
    "※ベッドは、ベビーベッド",
)



def integer(value: Any, *, field: str, row_no: int, allow_blank: bool = True) -> int:
    text = RowSupport.clean_cell(value)
    if not text:
        if allow_blank:
            return 0
        raise RuntimeError(f"row {row_no}: blank {field}")
    try:
        number = float(text)
    except ValueError as exc:
        raise RuntimeError(f"row {row_no}: invalid {field}={text!r}") from exc
    if not number.is_integer() or number < 0:
        raise RuntimeError(f"row {row_no}: invalid {field}={text!r}")
    return int(number)


def marker(value: Any, *, field: str, row_no: int) -> str:
    text = RowSupport.clean_cell(value)
    if text in ("", "○", "〇", "△"):
        return text
    raise RuntimeError(f"row {row_no}: unexpected {field} marker={text!r}")


def _validate_structure(values: list[tuple[Any, ...]], cfg: dict) -> None:
    if len(values) != 42:
        raise RuntimeError(f"14204: physical rows={len(values)} expected=42")

    for offset, expected in enumerate(EXPECTED_HEADER_ROWS, start=2):
        actual = tuple(RowSupport.clean_cell(v) for v in values[offset - 1][:12])
        if actual != expected:
            raise RuntimeError(
                f"14204: unexpected header row {offset}: "
                f"actual={actual!r} expected={expected!r}"
            )

    internal = tuple(RowSupport.clean_cell(v) for v in values[4][:12])
    expected_internal = (
        "列1", "列2", "列3", "列10", "列11", "列12",
        "列13", "列14", "列15", "列16", "列17", "列18",
    )
    if internal != expected_internal:
        raise RuntimeError(
            f"14204: unexpected internal header: "
            f"actual={internal!r} expected={expected_internal!r}"
        )

    notes = tuple(RowSupport.clean_cell(values[row_no - 1][9]) for row_no in range(40, 43))
    if notes != EXPECTED_FOOTER_NOTES:
        raise RuntimeError(
            f"14204: unexpected footer notes: actual={notes!r} "
            f"expected={EXPECTED_FOOTER_NOTES!r}"
        )


def prepare_one(code: str, cfg: dict, schema: list[str]):
    src = ROOT / "data/raw" / cfg["pref"] / cfg["mun"] / "public-toilet" / cfg["source"]
    dest = ROOT / "data/normalized" / cfg["pref"] / cfg["mun"] / "public-toilet/public-toilet.csv"

    if not src.exists():
        raise RuntimeError(f"{code}: raw missing: {src}")
    if dest.exists():
        raise RuntimeError(f"{code}: normalized already exists: {dest}")

    values = read_xlsx_values(src, cfg["sheet"])
    _validate_structure(values, cfg)

    code6 = six_digit_municipality_code(code)
    rows: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    for sheet_row in range(6, 40):
        source = values[sheet_row - 1]
        if len(source) < 12:
            source = (*source, *(None for _ in range(12 - len(source))))

        ident = RowSupport.clean_cell(source[0])
        name = RowSupport.clean_cell(source[1])
        address = RowSupport.clean_cell(source[2])
        if not ident or not name or not address:
            raise RuntimeError(
                f"{code}: row {sheet_row}: required value missing "
                f"ID={ident!r} name={name!r} address={address!r}"
            )
        if ident in seen_ids:
            raise RuntimeError(f"{code}: duplicate ID={ident!r}")
        seen_ids.add(ident)

        total = integer(source[3], field="便器数合計", row_no=sheet_row, allow_blank=False)
        male_w = integer(source[4], field="男和", row_no=sheet_row)
        male_western = integer(source[5], field="男洋", row_no=sheet_row)
        male_urinal = integer(source[6], field="男小", row_no=sheet_row)
        female_w = integer(source[7], field="女和", row_no=sheet_row)
        female_western = integer(source[8], field="女洋", row_no=sheet_row)
        accessible = integer(source[9], field="身障", row_no=sheet_row)
        ostomy = marker(source[10], field="オスト", row_no=sheet_row)
        baby_bed = marker(source[11], field="ベッド", row_no=sheet_row)

        male_total = male_w + male_western + male_urinal
        female_total = female_w + female_western
        computed_total = male_total + female_total + accessible
        if computed_total != total:
            raise RuntimeError(
                f"{code}: row {sheet_row}: total mismatch "
                f"source={total} computed={computed_total}"
            )

        row = {column: "" for column in schema}
        row["全国地方公共団体コード"] = code6
        row["ID"] = ident
        row["地方公共団体名"] = cfg["name"]
        row["名称"] = name
        row["所在地_全国地方公共団体コード"] = code6
        row["所在地_連結表記"] = f"神奈川県鎌倉市{address}"
        row["所在地_都道府県"] = "神奈川県"
        row["所在地_市区町村"] = "鎌倉市"
        row["男性トイレ総数"] = str(male_total)
        row["男性トイレ数（小便器）"] = str(male_urinal)
        row["男性トイレ数（和式）"] = str(male_w)
        row["男性トイレ数（洋式）"] = str(male_western)
        row["女性トイレ総数"] = str(female_total)
        row["女性トイレ数（和式）"] = str(female_w)
        row["女性トイレ数（洋式）"] = str(female_western)
        row["車椅子使用者用トイレ有無"] = "有" if accessible > 0 else "無"

        if ostomy in ("○", "〇"):
            row["オストメイト設置トイレ有無"] = "有"
        elif ostomy == "△":
            RowSupport.append_note(row, "原データオスト=△")

        if baby_bed in ("○", "〇"):
            row["乳幼児用設備設置トイレ有無"] = "有"
        elif baby_bed == "△":
            RowSupport.append_note(row, "原データベッド=△")

        RowSupport.append_note(row, f"原データ便器数合計={total}")
        if accessible > 0:
            RowSupport.append_note(row, f"原データ車いす対応便器数={accessible}")

        rows.append(row)

    if not rows:
        raise RuntimeError(f"{code}: no data rows")

    return src, dest, rows



def main() -> None:
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    prepared = []
    for code, cfg in TARGETS.items():
        src, dest, rows = prepare_one(code, cfg, schema)
        prepared.append((code, cfg, src, dest, rows))

    print(f"preflight OK: {len(prepared)} municipalities")

    for code, cfg, src, dest, rows in prepared:
        StandardCsvWriter().write(dest, schema, rows)
        print(
            f"OK {code} {cfg['mun']}: "
            f"rows={len(rows)} source={src.name} format=xlsx"
        )


if __name__ == "__main__":
    main()
