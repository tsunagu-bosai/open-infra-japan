#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.normalization import RowSupport, StandardCsvWriter
from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.xlsx import read_xlsx_values

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "26100": {
        "pref": "26-京都府",
        "mun": "26100-京都市",
        "name": "京都府京都市",
        "source": "20260904111633_オープンデータ（公衆トイレ、観光トイレ）修正.xlsx",
        "sheet": "公衆・観光トイレ",
    },
}

EXPECTED_HEADER = (
    "番号",
    "施設名",
    "施設名よみがな",
    "公衆トイレマップ番号",
    "行政区",
    "所在地",
    "経度",
    "緯度",
    "ＨＰ（ＵＲＬ）",
    "開放時間",
    "ベビー\n対応",
    "オストメイト\n対応",
    "車いす\n対応",
    "洋式化\n対応",
    "ウォシュレット\n対応",
    "便器数",
)

_FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")
_SIMPLE_TIME_RE = re.compile(
    r"^(午前|午後)(\d{1,2})時(?:(\d{1,2})分)?から"
    r"(午前|午後)(\d{1,2})時(?:(\d{1,2})分)?まで$"
)



def one_line(value: Any) -> str:
    return " ".join(RowSupport.clean_cell(value).replace("\u3000", " ").split())


def ascii_digits(text: str) -> str:
    return text.translate(_FULLWIDTH_DIGITS)



def yes_no(value: Any, *, field: str, row_no: int) -> str:
    text = RowSupport.clean_cell(value)
    if text == "○":
        return "有"
    if text == "×":
        return "無"
    raise RuntimeError(f"26100: row {row_no}: unexpected {field}={text!r}")


def _clock(period: str, hour_text: str, minute_text: str, *, is_end: bool) -> str:
    hour = int(hour_text)
    minute = int(minute_text or "0")
    if not 0 <= minute <= 59:
        raise RuntimeError(f"invalid minute: {minute}")

    if period == "午前":
        if hour == 0 and is_end:
            return "23:59"
        if not 0 <= hour <= 11:
            raise RuntimeError(f"invalid AM hour: {hour}")
    else:
        if not 0 <= hour <= 12:
            raise RuntimeError(f"invalid PM hour: {hour}")
        if hour < 12:
            hour += 12

    return f"{hour:02d}:{minute:02d}"


def normalize_open_time(value: Any, *, row_no: int) -> tuple[str, str, str]:
    original = RowSupport.clean_cell(value)
    compact = ascii_digits(original.replace("\n", "").replace("\r", "").replace("　", "").strip())

    if compact == "終日":
        return "00:00", "23:59", ""

    if "終日" in compact or "頃" in compact or "（" in compact or "(" in compact:
        return "", "", one_line(original)

    match = _SIMPLE_TIME_RE.fullmatch(compact)
    if not match:
        raise RuntimeError(f"26100: row {row_no}: unsupported 開放時間={original!r}")

    start = _clock(match.group(1), match.group(2), match.group(3) or "", is_end=False)
    end = _clock(match.group(4), match.group(5), match.group(6) or "", is_end=True)
    return start, end, ""


def _count_matches(pattern: str, text: str) -> int:
    values = [int(value) for value in re.findall(pattern, text)]
    if len(values) > 1:
        raise RuntimeError(f"multiple count matches: pattern={pattern!r} text={text!r}")
    return values[0] if values else 0


def parse_fixture_counts(value: Any, *, row_no: int) -> dict[str, int]:
    original = ascii_digits(RowSupport.clean_cell(value).replace("\r", ""))
    if not original:
        raise RuntimeError(f"26100: row {row_no}: blank 便器数")

    totals = {
        "male_total": 0,
        "male_urinal": 0,
        "female_total": 0,
        "shared_total": 0,
    }

    for raw_line in original.split("\n"):
        line = raw_line.strip().replace("　", "")
        if not line:
            continue
        if line.startswith("※"):
            if "女性専用" not in line:
                raise RuntimeError(f"26100: row {row_no}: unsupported fixture note={raw_line!r}")
            continue
        if re.fullmatch(r"多(?:機能|目的)\d+室", line):
            continue

        if line.startswith(("男子", "男性用")):
            category = "male"
        elif line.startswith(("女子", "女性用")) or "女性専用" in line:
            category = "female"
        elif "男女共用" in line:
            category = "shared"
        else:
            raise RuntimeError(f"26100: row {row_no}: unsupported fixture line={raw_line!r}")

        urinal = _count_matches(r"小便(?:器)?(\d+)基", line)
        big = _count_matches(r"大便器(\d+)基", line)
        if urinal == 0 and big == 0:
            raise RuntimeError(f"26100: row {row_no}: no fixture count in line={raw_line!r}")

        if category == "male":
            totals["male_urinal"] += urinal
            totals["male_total"] += urinal + big
        elif category == "female":
            totals["female_total"] += urinal + big
        else:
            totals["shared_total"] += urinal + big

    return totals


def build_address(ward: str, source_address: str) -> tuple[str, str, str]:
    ward = RowSupport.clean_cell(ward)
    source_address = RowSupport.clean_cell(source_address)
    if not ward or not source_address:
        raise RuntimeError(
            f"26100: blank address component: ward={ward!r} address={source_address!r}"
        )

    city_ward = f"京都市{ward}"
    if source_address.startswith("京都市"):
        full = f"京都府{source_address}"
        prefix = city_ward
        town = source_address[len(prefix):] if source_address.startswith(prefix) else source_address
    elif source_address.startswith(ward):
        full = f"京都府京都市{source_address}"
        town = source_address[len(ward):]
    else:
        full = f"京都府{city_ward}{source_address}"
        town = source_address

    return full, city_ward, town


def _validate_structure(values: list[tuple[Any, ...]], cfg: dict) -> None:
    if len(values) != 139:
        raise RuntimeError(f"26100: physical rows={len(values)} expected=139")

    header = tuple(RowSupport.clean_cell(v) for v in values[1][:16])
    if header != EXPECTED_HEADER:
        raise RuntimeError(
            f"26100: unexpected header: actual={header!r} expected={EXPECTED_HEADER!r}"
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

    for sheet_row in range(3, 139):
        source = values[sheet_row - 1]
        if len(source) < 16:
            source = (*source, *(None for _ in range(16 - len(source))))

        name = one_line(source[1])
        kana = one_line(source[2])
        ident = RowSupport.clean_cell(source[3])
        ward = RowSupport.clean_cell(source[4])
        address = RowSupport.clean_cell(source[5])
        longitude = RowSupport.clean_cell(source[6])
        latitude = RowSupport.clean_cell(source[7])
        url = RowSupport.clean_cell(source[8])

        if not ident or not name or not ward or not address:
            raise RuntimeError(
                f"{code}: row {sheet_row}: required value missing "
                f"ID={ident!r} name={name!r} ward={ward!r} address={address!r}"
            )
        if ident in seen_ids:
            raise RuntimeError(f"{code}: duplicate ID={ident!r}")
        seen_ids.add(ident)

        try:
            lon_value = float(longitude)
            lat_value = float(latitude)
        except ValueError as exc:
            raise RuntimeError(
                f"{code}: row {sheet_row}: invalid coordinate "
                f"longitude={longitude!r} latitude={latitude!r}"
            ) from exc
        if not 122 <= lon_value <= 154 or not 20 <= lat_value <= 46:
            raise RuntimeError(
                f"{code}: row {sheet_row}: coordinate out of Japan range "
                f"longitude={longitude!r} latitude={latitude!r}"
            )

        start, end, time_note = normalize_open_time(source[9], row_no=sheet_row)
        baby = yes_no(source[10], field="ベビー対応", row_no=sheet_row)
        ostomy = yes_no(source[11], field="オストメイト対応", row_no=sheet_row)
        wheelchair = yes_no(source[12], field="車いす対応", row_no=sheet_row)
        western = RowSupport.clean_cell(source[13])
        washlet = RowSupport.clean_cell(source[14])
        if western not in ("○", "×") or washlet not in ("○", "×"):
            raise RuntimeError(
                f"{code}: row {sheet_row}: unexpected equipment marker "
                f"western={western!r} washlet={washlet!r}"
            )

        counts = parse_fixture_counts(source[15], row_no=sheet_row)
        full_address, city_ward, town = build_address(ward, address)

        row = {column: "" for column in schema}
        row["全国地方公共団体コード"] = code6
        row["ID"] = ident
        row["地方公共団体名"] = cfg["name"]
        row["名称"] = name
        row["名称_カナ"] = kana
        row["所在地_全国地方公共団体コード"] = code6
        row["所在地_連結表記"] = full_address
        row["所在地_都道府県"] = "京都府"
        row["所在地_市区町村"] = city_ward
        row["所在地_町字"] = town
        row["緯度"] = latitude
        row["経度"] = longitude
        row["男性トイレ総数"] = str(counts["male_total"])
        row["男性トイレ数（小便器）"] = str(counts["male_urinal"])
        row["女性トイレ総数"] = str(counts["female_total"])
        row["男女共用トイレ総数"] = str(counts["shared_total"])
        row["車椅子使用者用トイレ有無"] = wheelchair
        row["乳幼児用設備設置トイレ有無"] = baby
        row["オストメイト設置トイレ有無"] = ostomy
        row["利用開始時間"] = start
        row["利用終了時間"] = end
        row["利用可能時間特記事項"] = time_note

        RowSupport.append_note(row, f"原データ便器数={one_line(source[15])}")
        RowSupport.append_note(row, f"原データ洋式化対応={western}")
        RowSupport.append_note(row, f"原データウォシュレット対応={washlet}")
        if url:
            RowSupport.append_note(row, f"原データHP={url}")

        rows.append(row)

    if not rows:
        raise RuntimeError(f"{code}: no data rows")
    if len(seen_ids) != len(rows):
        raise RuntimeError(f"{code}: normalized IDs are not unique")

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
