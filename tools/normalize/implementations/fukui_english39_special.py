#!/usr/bin/env python3
from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from tools import normalize_public_toilet as common
from tools.normalize.core.normalization import RowSupport, StandardCsvWriter
from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.schema import read_schema_fields

try:
    from .fukui_raw_common import load_english39_rows
except ImportError:  # direct execution
    from fukui_raw_common import load_english39_rows

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "18204": ("18204-小浜市", "小浜市"),
    "18205": ("18205-大野市", "大野市"),
    "18208": ("18208-あわら市", "あわら市"),
    "18209": ("18209-越前市", "越前市"),
    "18210": ("18210-坂井市", "坂井市"),
    "18322": ("18322-永平寺町", "永平寺町"),
}

ENGLISH39 = [
    "localgov_code", "id", "localgov_name", "name", "name_kana", "name_english",
    "seat_localgov_code", "choaza_id", "seat_copulative_spell", "seat_prefecture",
    "seat_city", "seat_choaza", "seat_after_address", "buillding_name_etc",
    "set_position", "latitude", "longitude", "advanced_classification",
    "advanced_value", "male_wc_total", "male_wc_urinal", "male_wc_jstyle",
    "male_wc_wstyle", "female_wc_total", "female_wc_jstyle", "female_wc_wstyle",
    "unisex_wc_total", "unisex_wc_jstyle", "unisex_wc_wstyle", "barrier_free_wc",
    "wheelchair_wc", "infant_wc", "ostomate_wc", "available_start_time",
    "available_end_time", "available_time_note", "image", "image_licence", "note",
]

DIRECT_MAP = {
    "id": "ID",
    "name": "名称",
    "name_kana": "名称_カナ",
    "name_english": "名称_英語",
    "seat_localgov_code": "所在地_全国地方公共団体コード",
    "choaza_id": "町字ID",
    "seat_copulative_spell": "所在地_連結表記",
    "seat_prefecture": "所在地_都道府県",
    "seat_city": "所在地_市区町村",
    "seat_choaza": "所在地_町字",
    "seat_after_address": "所在地_番地以下",
    "buillding_name_etc": "建物名等(方書)",
    "set_position": "設置位置",
    "latitude": "緯度",
    "longitude": "経度",
    "advanced_classification": "高度の種別",
    "advanced_value": "高度の値",
    "male_wc_total": "男性トイレ総数",
    "male_wc_urinal": "男性トイレ数（小便器）",
    "male_wc_jstyle": "男性トイレ数（和式）",
    "male_wc_wstyle": "男性トイレ数（洋式）",
    "female_wc_total": "女性トイレ総数",
    "female_wc_jstyle": "女性トイレ数（和式）",
    "female_wc_wstyle": "女性トイレ数（洋式）",
    "unisex_wc_total": "男女共用トイレ総数",
    "unisex_wc_jstyle": "男女共用トイレ数（和式）",
    "unisex_wc_wstyle": "男女共用トイレ数（洋式）",
    "barrier_free_wc": "バリアフリートイレ数",
    "image": "画像",
    "image_licence": "画像_ライセンス",
    "note": "備考",
}


def append_time_note(row, text):
    text = (text or "").strip()
    if not text:
        return
    cur = (row.get("利用可能時間特記事項") or "").strip()
    if cur == "なし":
        cur = ""
    if text in cur:
        row["利用可能時間特記事項"] = cur
        return
    row["利用可能時間特記事項"] = f"{cur} / {text}" if cur else text


def numeric_fraction_to_hhmm(v: str) -> str:
    d = Decimal(v)
    minutes = int((d * Decimal(1440)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if not (0 <= minutes < 1440):
        raise RuntimeError(f"Excel time fraction out of range: {v!r}")
    h, m = divmod(minutes, 60)
    return f"{h:02d}:{m:02d}"


def normalize_basic_time(v: str, row, source_name: str) -> str:
    v = (v or "").strip()
    if not v:
        return ""

    if re.fullmatch(r"0?\.\d+", v):
        hhmm = numeric_fraction_to_hhmm(v)
        RowSupport.append_note(row, f"原データ{source_name}={v}")
        return hhmm

    m = re.fullmatch(r"(\d{1,2}):(\d{2})", v)
    if m:
        h, minute = map(int, m.groups())
        if not (0 <= h <= 23 and 0 <= minute <= 59):
            raise RuntimeError(f"invalid time {source_name}={v!r}")
        return f"{h:02d}:{minute:02d}"

    return ""


def normalize_bool(municipality: str, field: str, value: str, row) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    if v in ("有", "無"):
        return v

    # 小浜: infant_wc is 1/2 (count-like), ostomate_wc is numeric.
    # Do not squeeze count-like source values into canonical boolean fields.
    if municipality == "小浜市" and field in ("infant_wc", "ostomate_wc") and v.isdigit():
        RowSupport.append_note(row, f"原データ{field}={v}")
        return ""

    # 越前市役所本庁舎: 11/17/4 are clearly counts, not booleans.
    if municipality == "越前市" and field in ("wheelchair_wc", "infant_wc", "ostomate_wc") and v.isdigit():
        RowSupport.append_note(row, f"原データ{field}={v}")
        return ""

    # 永平寺: 0/1/3 and 0 values are count-like. Preserve without collapsing.
    if municipality == "永平寺町" and field in ("wheelchair_wc", "infant_wc", "ostomate_wc") and v.isdigit():
        RowSupport.append_note(row, f"原データ{field}={v}")
        return ""

    # 大野・坂井: isolated "1" occurs in columns otherwise using 有/無,
    # so normalize as affirmative while preserving source representation.
    if municipality in ("大野市", "坂井市") and v == "1":
        RowSupport.append_note(row, f"原データ{field}=1")
        return "有"

    raise RuntimeError(f"{municipality}: unexpected {field}={v!r}")


def normalize_times(municipality: str, c: dict, row):
    start = (c["available_start_time"] or "").strip()
    end = (c["available_end_time"] or "").strip()
    note = (c["available_time_note"] or "").strip()

    # "なし" means no special note.
    row["利用可能時間特記事項"] = "" if note == "なし" else note

    # 永平寺: explicit 24時間 in both time fields.
    if municipality == "永平寺町" and start == "24時間" and end == "24時間":
        row["利用開始時間"] = "00:00"
        row["利用終了時間"] = "23:59"
        RowSupport.append_note(row, "原データavailable_start_time=24時間")
        RowSupport.append_note(row, "原データavailable_end_time=24時間")
        return

    # 永平寺: "10:0024時間" / "17:0024時間" is a composite source value;
    # it cannot be represented safely as a single clock range.
    if municipality == "永平寺町" and ("24時間" in start or "24時間" in end):
        if start:
            append_time_note(row, f"原データ利用開始時間={start}")
            RowSupport.append_note(row, f"原データavailable_start_time={start}")
        if end:
            append_time_note(row, f"原データ利用終了時間={end}")
            RowSupport.append_note(row, f"原データavailable_end_time={end}")
        row["利用開始時間"] = ""
        row["利用終了時間"] = ""
        return

    # 越前: explicit full-day availability.
    if municipality == "越前市" and start == "常時利用可能":
        row["利用開始時間"] = "00:00"
        row["利用終了時間"] = "23:59"
        RowSupport.append_note(row, "原データavailable_start_time=常時利用可能")
        if end:
            RowSupport.append_note(row, f"原データavailable_end_time={end}")
        return

    # 越前: Japanese textual times.
    jp_times = {
        "午前９時": "09:00",
        "午前１０時": "10:00",
        "午後６時": "18:00",
        "午後１０時": "22:00",
    }
    if municipality == "越前市" and (start in jp_times or end in jp_times):
        if start:
            if start not in jp_times:
                raise RuntimeError(f"{municipality}: mixed unexpected start={start!r}")
            row["利用開始時間"] = jp_times[start]
            RowSupport.append_note(row, f"原データavailable_start_time={start}")
        if end:
            if end not in jp_times:
                raise RuntimeError(f"{municipality}: mixed unexpected end={end!r}")
            row["利用終了時間"] = jp_times[end]
            RowSupport.append_note(row, f"原データavailable_end_time={end}")
        return

    # 越前: floor-specific closing times cannot be collapsed to one value.
    if municipality == "越前市" and end == "23:30（３階） 21:00（４階）":
        row["利用開始時間"] = normalize_basic_time(start, row, "available_start_time")
        row["利用終了時間"] = ""
        append_time_note(row, f"原データ利用終了時間={end}")
        RowSupport.append_note(row, f"原データavailable_end_time={end}")
        return

    row["利用開始時間"] = normalize_basic_time(start, row, "available_start_time")
    row["利用終了時間"] = normalize_basic_time(end, row, "available_end_time")

    if start and not row["利用開始時間"]:
        raise RuntimeError(f"{municipality}: unhandled start time={start!r}")
    if end and not row["利用終了時間"]:
        raise RuntimeError(f"{municipality}: unhandled end time={end!r}")


def normalize_coordinates(municipality: str, row):
    lat = (row["緯度"] or "").strip()
    lon = (row["経度"] or "").strip()

    if lat:
        try:
            x = float(lat)
        except ValueError:
            RowSupport.append_note(row, f"原データ緯度={lat}")
            row["緯度"] = ""
        else:
            if not (20 <= x <= 50):
                RowSupport.append_note(row, f"原データ緯度={lat}")
                row["緯度"] = ""

    if lon:
        try:
            x = float(lon)
        except ValueError:
            RowSupport.append_note(row, f"原データ経度={lon}")
            row["経度"] = ""
        else:
            if not (120 <= x <= 155):
                # Do not guess that 13.195587 means 136.195587.
                RowSupport.append_note(row, f"原データ経度={lon}")
                row["経度"] = ""


def main():
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    prepared = []

    for code5, (mun_dir, municipality) in TARGETS.items():
        source_path, srcrows = load_english39_rows(
            ROOT, code5, mun_dir, municipality
        )
        path = ROOT / "data/normalized/18-福井県" / mun_dir / "public-toilet/public-toilet.csv"

        out = []
        invalid_coordinates_cleared = 0
        for line_no, src in enumerate(srcrows, 2):
            c = {k: (v or "").strip() for k, v in src.items()}
            row = {k: "" for k in schema}

            row["全国地方公共団体コード"] = six_digit_municipality_code(code5)
            row["地方公共団体名"] = municipality

            for old, new in DIRECT_MAP.items():
                row[new] = c[old]

            if c["localgov_name"] and c["localgov_name"] != municipality:
                RowSupport.append_note(row, f"原データ地方公共団体名={c['localgov_name']}")

            row["車椅子使用者用トイレ有無"] = normalize_bool(
                municipality, "wheelchair_wc", c["wheelchair_wc"], row
            )
            row["乳幼児用設備設置トイレ有無"] = normalize_bool(
                municipality, "infant_wc", c["infant_wc"], row
            )
            row["オストメイト設置トイレ有無"] = normalize_bool(
                municipality, "ostomate_wc", c["ostomate_wc"], row
            )

            normalize_times(municipality, c, row)

            before_lat, before_lon = row["緯度"], row["経度"]
            normalize_coordinates(municipality, row)
            if before_lat and not row["緯度"]:
                invalid_coordinates_cleared += 1
            if before_lon and not row["経度"]:
                invalid_coordinates_cleared += 1

            out.append(row)

        ids = [r["ID"] for r in out if r["ID"]]
        if len(ids) != len(set(ids)):
            raise RuntimeError(f"{code5}: duplicate nonblank IDs")

        patches = common.load_patches("18-福井県", mun_dir)

        if patches:
            applied, problems = common.apply_patches(
                out,
                patches,
                source_path,
            )
            if problems:
                raise RuntimeError(
                    f"{mun_dir}: patch errors: "
                    + " | ".join(problems)
                )
            print(
                f"{code5} {municipality}: patches applied={applied}"
            )

        prepared.append((code5, municipality, path, out, invalid_coordinates_cleared))

    print(f"preflight OK: {len(prepared)} municipalities")
    for code5, municipality, path, rows, invalid_coordinates_cleared in prepared:
        StandardCsvWriter().write(path, schema, rows)
        print(
            f"OK {code5} {municipality}: rows={len(rows)} code={six_digit_municipality_code(code5)} "
            f"invalid_coordinates_cleared={invalid_coordinates_cleared}"
        )


if __name__ == "__main__":
    main()
