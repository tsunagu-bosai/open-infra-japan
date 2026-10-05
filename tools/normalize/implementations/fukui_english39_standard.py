#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
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
    "18201": ("18201-福井市", "福井市"),
    "18202": ("18202-敦賀市", "敦賀市"),
    "18206": ("18206-勝山市", "勝山市"),
    "18404": ("18404-南越前町", "南越前町"),
    "18423": ("18423-越前町", "越前町"),
    "18442": ("18442-美浜町", "美浜町"),
    "18481": ("18481-高浜町", "高浜町"),
    "18483": ("18483-おおい町", "おおい町"),
    "18501": ("18501-若狭町", "若狭町"),
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
    if text in cur:
        return
    row["利用可能時間特記事項"] = f"{cur} / {text}" if cur else text


def normalize_bool(value: str, row, source_name: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    if v in ("有", "無"):
        return v
    # 敦賀市のように「有 + 設備詳細」となっているケース。
    if v.startswith("有"):
        RowSupport.append_note(row, f"原データ{source_name}={v}")
        return "有"
    raise RuntimeError(f"unexpected boolean-like value {source_name}={v!r}")


def normalize_time(value: str, row, source_name: str, municipality: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""

    # 南越前町: 時刻列に説明文が入っている。構造時刻には入れず特記事項へ。
    if municipality == "南越前町" and v == "シーズン毎に違うためHP参照のこと":
        append_time_note(row, v)
        RowSupport.append_note(row, f"原データ{source_name}={v}")
        return ""

    # 高浜町: 終了時刻に注記が連結されている。
    if municipality == "高浜町" and source_name == "available_end_time":
        m = re.fullmatch(r"(\d{1,2}):(\d{2})※(.+)", v)
        if m:
            h, minute, note = m.groups()
            hhmm = f"{int(h):02d}:{int(minute):02d}"
            append_time_note(row, f"{hhmm}※{note}")
            RowSupport.append_note(row, f"原データavailable_end_time={v}")
            return hhmm

    m = re.fullmatch(r"(\d{1,2}):(\d{2})", v)
    if not m:
        raise RuntimeError(f"unexpected time {source_name}={v!r}")
    h, minute = map(int, m.groups())
    if not (0 <= h <= 23 and 0 <= minute <= 59):
        raise RuntimeError(f"invalid time {source_name}={v!r}")
    return f"{h:02d}:{minute:02d}"


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

        rows = []
        detailed_bool = 0
        time_text_moved = 0

        for line_no, src in enumerate(srcrows, 2):
            c = {k: (v or "").strip() for k, v in src.items()}
            row = {k: "" for k in schema}

            row["全国地方公共団体コード"] = six_digit_municipality_code(code5)
            row["地方公共団体名"] = municipality

            for old, new in DIRECT_MAP.items():
                row[new] = c[old]

            if c["localgov_name"] and c["localgov_name"] != municipality:
                RowSupport.append_note(row, f"原データ地方公共団体名={c['localgov_name']}")

            before_note = row["備考"]
            row["車椅子使用者用トイレ有無"] = normalize_bool(
                c["wheelchair_wc"], row, "wheelchair_wc"
            )
            row["乳幼児用設備設置トイレ有無"] = normalize_bool(
                c["infant_wc"], row, "infant_wc"
            )
            row["オストメイト設置トイレ有無"] = normalize_bool(
                c["ostomate_wc"], row, "ostomate_wc"
            )
            if row["備考"] != before_note:
                detailed_bool += 1

            row["利用可能時間特記事項"] = c["available_time_note"]

            before_time_note = row["利用可能時間特記事項"]
            row["利用開始時間"] = normalize_time(
                c["available_start_time"], row, "available_start_time", municipality
            )
            row["利用終了時間"] = normalize_time(
                c["available_end_time"], row, "available_end_time", municipality
            )
            if row["利用可能時間特記事項"] != before_time_note:
                time_text_moved += 1

            rows.append(row)

        ids = [r["ID"] for r in rows if r["ID"]]
        if len(ids) != len(set(ids)):
            raise RuntimeError(f"{code5}: duplicate nonblank IDs")

        prepared.append((code5, municipality, path, rows, detailed_bool, time_text_moved))

    print(f"preflight OK: {len(prepared)} municipalities")

    for code5, municipality, path, rows, detailed_bool, time_text_moved in prepared:
        StandardCsvWriter().write(path, schema, rows)
        print(
            f"OK {code5} {municipality}: rows={len(rows)} code={six_digit_municipality_code(code5)} "
            f"detailed_bool_preserved={detailed_bool} time_text_moved={time_text_moved}"
        )


if __name__ == "__main__":
    main()
