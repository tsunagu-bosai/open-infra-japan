#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

try:
    import xlrd
except ImportError as exc:
    raise RuntimeError("xls処理に xlrd が必要です") from exc

from tools import normalize_public_toilet as common
from tools.normalize.core.normalization import (
    LenientEndOfDayTimeStrategy,
    RowSupport,
    StandardCsvWriter,
    ValueCleaner,
)

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "schema/standard/public-toilet/schema.csv"
RAW = ROOT / "data/raw"
OUT = ROOT / "data/normalized"

TARGETS = {
    "20202": ("松本市", "opendata_31.csv"),
    "20203": ("上田市", "74470.csv"),
    "20205": ("飯田市", "74961.csv"),
    "20207": ("須坂市", "202070_public_toilet.xls"),
}

PLACEHOLDERS = {"-", "ー", "－"}
CLEANER = ValueCleaner(PLACEHOLDERS)


def schema_fields() -> list[str]:
    with SCHEMA.open("r", encoding="utf-8-sig", newline="") as f:
        return [r["name"] for r in csv.DictReader(f)]


def blank_row(fields: list[str]) -> dict[str, str]:
    return {k: "" for k in fields}



TIME_NORMALIZER = LenientEndOfDayTimeStrategy(cleaner=CLEANER)



def read_csv_rows(path: Path, encoding: str):
    with path.open("r", encoding=encoding, newline="") as f:
        return list(csv.DictReader(f))



def apply_patches(pref_dir: str, muni_dir: str, rows, source: Path) -> int:
    patches = common.load_patches(pref_dir, muni_dir)
    applied, problems = common.apply_patches(rows, patches, source)
    if problems:
        raise RuntimeError(
            f"{muni_dir}: patch適用失敗: " + " | ".join(map(str, problems))
        )
    return applied


def output_path(pref_dir: str, muni_dir: str) -> Path:
    return OUT / pref_dir / muni_dir / "public-toilet/public-toilet.csv"


def normalize_matsumoto(fields: list[str]):
    pref_dir, muni_dir = "20-長野県", "20202-松本市"
    source = RAW / pref_dir / muni_dir / "public-toilet/opendata_31.csv"
    src = read_csv_rows(source, "utf-8-sig")
    rows = []

    for r in src:
        if CLEANER(r.get("分類")) != "公衆トイレ":
            continue
        row = blank_row(fields)
        code6 = "202029"
        address = CLEANER(r.get("所在地"))

        row["全国地方公共団体コード"] = code6
        row["ID"] = CLEANER(r.get("管理番号"))
        row["地方公共団体名"] = "長野県松本市"
        row["名称"] = CLEANER(r.get("名称"))
        row["名称_カナ"] = CLEANER(r.get("読み"))
        row["所在地_全国地方公共団体コード"] = code6
        row["所在地_連結表記"] = f"長野県松本市{address}" if address else ""
        row["所在地_都道府県"] = "長野県"
        row["所在地_市区町村"] = "松本市"
        row["所在地_番地以下"] = address
        row["緯度"] = CLEANER(r.get("緯度"))
        row["経度"] = CLEANER(r.get("経度"))
        row["車椅子使用者用トイレ有無"] = CLEANER(r.get("身障者用"))

        notes = []
        if CLEANER(r.get("所管課")):
            notes.append("所管課:" + CLEANER(r.get("所管課")))
        if CLEANER(r.get("備考")):
            notes.append(CLEANER(r.get("備考")))
        if CLEANER(r.get("分類")):
            notes.append("分類:" + CLEANER(r.get("分類")))
        row["備考"] = " / ".join(notes)
        rows.append(row)

    applied = apply_patches(pref_dir, muni_dir, rows, source)
    return pref_dir, muni_dir, source, rows, applied


def normalize_ueda(fields: list[str]):
    pref_dir, muni_dir = "20-長野県", "20203-上田市"
    source = RAW / pref_dir / muni_dir / "public-toilet/74470.csv"
    src = read_csv_rows(source, "cp932")
    rows = []

    for r in src:
        no = CLEANER(r.get("NO"))
        if not no.isdigit():
            continue
        row = blank_row(fields)
        code6 = "202037"
        address = CLEANER(r.get("住所"))
        # 住所欄の1件に市名が含まれるため、所在地_番地以下では重複を除く。
        address_after_city = address
        if address_after_city.startswith("上田市"):
            address_after_city = address_after_city[len("上田市"):].strip()

        row["全国地方公共団体コード"] = code6
        row["ID"] = no
        row["地方公共団体名"] = "長野県上田市"
        row["名称"] = CLEANER(r.get("名称"))
        row["名称_カナ"] = CLEANER(r.get("名称_カナ"))
        row["所在地_全国地方公共団体コード"] = code6
        row["所在地_連結表記"] = (
            f"長野県上田市{address_after_city}" if address_after_city else ""
        )
        row["所在地_都道府県"] = "長野県"
        row["所在地_市区町村"] = "上田市"
        row["所在地_番地以下"] = address_after_city
        row["建物名等(方書)"] = CLEANER(r.get("方書"))
        row["設置位置"] = CLEANER(r.get("設置位置"))
        row["緯度"] = CLEANER(r.get("緯度"))
        row["経度"] = CLEANER(r.get("経度"))
        row["乳幼児用設備設置トイレ有無"] = CLEANER(
            r.get("乳幼児用設備トイレ併設有無")
        )

        availability = [
            CLEANER(r.get("利用可能日")),
            CLEANER(r.get("利用可能時間")),
        ]
        row["利用可能時間特記事項"] = " / ".join(x for x in availability if x)
        row["備考"] = CLEANER(r.get("備考"))
        rows.append(row)

    applied = apply_patches(pref_dir, muni_dir, rows, source)
    return pref_dir, muni_dir, source, rows, applied


def normalize_iida(fields: list[str]):
    pref_dir, muni_dir = "20-長野県", "20205-飯田市"
    source = RAW / pref_dir / muni_dir / "public-toilet/74961.csv"
    src = read_csv_rows(source, "utf-8-sig")
    rows = []

    direct_fields = [
        "全国地方公共団体コード", "名称", "名称_カナ", "名称_英語",
        "所在地_全国地方公共団体コード", "町字ID", "所在地_連結表記",
        "所在地_都道府県", "所在地_市区町村", "所在地_町字",
        "所在地_番地以下", "建物名等(方書)", "設置位置", "緯度", "経度",
        "高度の種別", "高度の値", "バリアフリートイレ数",
        "車椅子使用者用トイレ有無", "乳幼児用設備設置トイレ有無",
        "オストメイト設置トイレ有無", "利用可能時間特記事項",
        "画像", "画像_ライセンス", "備考",
    ]

    for r in src:
        row = blank_row(fields)
        for field in direct_fields:
            # 飯田市の既存patchは source の "-" を original_value として
            # 照合するため、patch適用前はプレースホルダを保持する。
            value = r.get(field)
            row[field] = "" if value is None else str(value).strip()

        row["ID"] = CLEANER(r.get("データセット_ID"))
        row["地方公共団体名"] = "長野県飯田市"
        row["利用開始時間"] = TIME_NORMALIZER(r.get("利用開始時間"))
        row["利用終了時間"] = TIME_NORMALIZER(r.get("利用終了時間"))
        rows.append(row)

    applied = apply_patches(pref_dir, muni_dir, rows, source)
    return pref_dir, muni_dir, source, rows, applied


def read_xls_table(source: Path, header_row: int):
    book = xlrd.open_workbook(source)
    sheet = book.sheet_by_index(0)

    def cell(r, c):
        v = sheet.cell_value(r, c)
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        return str(v).strip()

    header = [cell(header_row, c) for c in range(sheet.ncols)]
    rows = []
    for r in range(header_row + 1, sheet.nrows):
        values = [cell(r, c) for c in range(sheet.ncols)]
        if not any(values):
            continue
        rows.append({header[c]: values[c] for c in range(len(header)) if header[c]})
    return rows


def normalize_suzaka(fields: list[str]):
    pref_dir, muni_dir = "20-長野県", "20207-須坂市"
    source = RAW / pref_dir / muni_dir / "public-toilet/202070_public_toilet.xls"
    src = read_xls_table(source, 0)
    rows = []

    mapping = {
        "NO": "ID",
        "名称": "名称",
        "名称_カナ": "名称_カナ",
        "名称_英語": "名称_英語",
        "住所": "所在地_連結表記",
        "方書": "建物名等(方書)",
        "設置位置": "設置位置",
        "http://www.w3.org/2003/01/geo/wgs84_pos#lat": "緯度",
        "http://www.w3.org/2003/01/geo/wgs84_pos#long": "経度",
        "男性トイレ総数": "男性トイレ総数",
        "男性トイレ数（小便器）": "男性トイレ数（小便器）",
        "男性トイレ数（和式）": "男性トイレ数（和式）",
        "男性トイレ数（洋式）": "男性トイレ数（洋式）",
        "女性トイレ総数": "女性トイレ総数",
        "女性トイレ数（和式）": "女性トイレ数（和式）",
        "女性トイレ数（洋式）": "女性トイレ数（洋式）",
        "男女共用トイレ総数": "男女共用トイレ総数",
        "男女共用トイレ数（和式）": "男女共用トイレ数（和式）",
        "男女共用トイレ数（洋式）": "男女共用トイレ数（洋式）",
        "車椅子使用者用トイレ有無": "車椅子使用者用トイレ有無",
        "乳幼児用設備設置トイレ有無": "乳幼児用設備設置トイレ有無",
        "オストメイト設置トイレ有無": "オストメイト設置トイレ有無",
        "利用可能時間特記事項": "利用可能時間特記事項",
        "画像": "画像",
        "画像_ライセンス": "画像_ライセンス",
        "備考": "備考",
    }

    for r in src:
        no = CLEANER(r.get("NO"))
        if not no.isdigit():
            continue
        row = blank_row(fields)
        for source_field, target_field in mapping.items():
            row[target_field] = CLEANER(r.get(source_field))

        row["全国地方公共団体コード"] = "202070"
        row["所在地_全国地方公共団体コード"] = "202070"
        row["地方公共団体名"] = "長野県須坂市"
        row["所在地_都道府県"] = "長野県"
        row["所在地_市区町村"] = "須坂市"
        row["利用開始時間"] = TIME_NORMALIZER(r.get("利用開始時間"))
        row["利用終了時間"] = TIME_NORMALIZER(r.get("利用終了時間"))

        multi = CLEANER(r.get("多機能トイレ数"))
        if multi:
            RowSupport.append_note(row, f"多機能トイレ数:{multi}")
        rows.append(row)

    applied = apply_patches(pref_dir, muni_dir, rows, source)
    return pref_dir, muni_dir, source, rows, applied


def main():
    fields = schema_fields()
    if len(fields) != 39:
        raise RuntimeError(f"schema columns={len(fields)} expected=39")

    dispatch = {
        "20202": normalize_matsumoto,
        "20203": normalize_ueda,
        "20205": normalize_iida,
        "20207": normalize_suzaka,
    }

    prepared = []
    for code in TARGETS:
        prepared.append((code, dispatch[code](fields)))

    print(f"preflight OK: {len(prepared)} municipalities")

    for code, (pref_dir, muni_dir, source, rows, applied) in prepared:
        dest = output_path(pref_dir, muni_dir)
        StandardCsvWriter().write(dest, fields, rows)
        print(
            f"OK {muni_dir}: rows={len(rows)} "
            f"source={source.name} patches={applied}"
        )


if __name__ == "__main__":
    main()
