#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

RAW31 = [
    "都道府県名", "市区町村名", "名称", "名称_カナ", "名称_英語", "住所", "方書",
    "設置位置", "緯度", "経度", "男性トイレ総数", "男性トイレ数（小便器）",
    "男性トイレ数（和式）", "男性トイレ数（洋式）", "女性トイレ総数",
    "女性トイレ数（和式）", "女性トイレ数（洋式）", "男女共用トイレ総数",
    "男女共用トイレ数（和式）", "男女共用トイレ数（洋式）", "多機能トイレ数",
    "車椅子使用者用トイレ", "乳幼児用設備設置トイレ", "オストメイト設置トイレ",
    "利用開始時間", "利用終了時間", "利用可能時間特記事項", "休館日", "画像",
    "画像_ライセンス", "備考",
]

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


def _detect_encoding(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            pass
    raise RuntimeError(f"cannot decode {path}")


def _build_note(src: dict[str, str]) -> str:
    notes: list[str] = []
    if src["備考"]:
        notes.append(src["備考"])
    if src["多機能トイレ数"]:
        notes.append(f"多機能トイレ数:{src['多機能トイレ数']}")
    if src["休館日"]:
        notes.append(f"休館日:{src['休館日']}")
    return "; ".join(notes)


def _to_english39(src: dict[str, str], row_number: int) -> dict[str, str]:
    """Convert Fukui's 31-column source to the historical internal 39-column view.

    This is an in-memory compatibility layer only.  It is intentionally not written to
    data/normalized.  In particular, 多機能トイレ数 is preserved in note and is not
    treated as バリアフリートイレ数.
    """
    return {
        "localgov_code": "",
        "id": str(row_number),
        "localgov_name": f"{src['都道府県名']}{src['市区町村名']}",
        "name": src["名称"],
        "name_kana": src["名称_カナ"],
        "name_english": src["名称_英語"],
        "seat_localgov_code": "",
        "choaza_id": "",
        "seat_copulative_spell": src["住所"],
        "seat_prefecture": src["都道府県名"],
        "seat_city": src["市区町村名"],
        "seat_choaza": "",
        "seat_after_address": "",
        "buillding_name_etc": src["方書"],
        "set_position": src["設置位置"],
        "latitude": src["緯度"],
        "longitude": src["経度"],
        "advanced_classification": "",
        "advanced_value": "",
        "male_wc_total": src["男性トイレ総数"],
        "male_wc_urinal": src["男性トイレ数（小便器）"],
        "male_wc_jstyle": src["男性トイレ数（和式）"],
        "male_wc_wstyle": src["男性トイレ数（洋式）"],
        "female_wc_total": src["女性トイレ総数"],
        "female_wc_jstyle": src["女性トイレ数（和式）"],
        "female_wc_wstyle": src["女性トイレ数（洋式）"],
        "unisex_wc_total": src["男女共用トイレ総数"],
        "unisex_wc_jstyle": src["男女共用トイレ数（和式）"],
        "unisex_wc_wstyle": src["男女共用トイレ数（洋式）"],
        "barrier_free_wc": "",
        "wheelchair_wc": src["車椅子使用者用トイレ"],
        "infant_wc": src["乳幼児用設備設置トイレ"],
        "ostomate_wc": src["オストメイト設置トイレ"],
        "available_start_time": src["利用開始時間"],
        "available_end_time": src["利用終了時間"],
        "available_time_note": src["利用可能時間特記事項"],
        "image": src["画像"],
        "image_licence": src["画像_ライセンス"],
        "note": _build_note(src),
    }


def load_english39_rows(
    root: Path,
    code5: str,
    municipality_dir: str,
    municipality_name: str,
) -> tuple[Path, list[dict[str, str]]]:
    raw_dir = root / "data/raw/18-福井県" / municipality_dir / "public-toilet"
    files = sorted(raw_dir.glob("*.csv"))
    if len(files) != 1:
        raise RuntimeError(
            f"{code5}: expected exactly one raw CSV in {raw_dir}, got {len(files)}"
        )

    path = files[0]
    encoding = _detect_encoding(path)
    with path.open("r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        if header != RAW31:
            raise RuntimeError(f"{code5}: unexpected Fukui raw schema: {header!r}")
        raw_rows = list(reader)

    rows: list[dict[str, str]] = []
    for row_number, raw in enumerate(raw_rows, 1):
        src = {k: (v or "") for k, v in raw.items()}
        if src["都道府県名"] != "福井県":
            raise RuntimeError(
                f"{code5}: row {row_number}: unexpected prefecture={src['都道府県名']!r}"
            )
        if src["市区町村名"] != municipality_name:
            raise RuntimeError(
                f"{code5}: row {row_number}: unexpected municipality="
                f"{src['市区町村名']!r}, expected {municipality_name!r}"
            )
        rows.append(_to_english39(src, row_number))

    return path, rows
