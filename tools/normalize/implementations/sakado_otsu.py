#!/usr/bin/env python3
from __future__ import annotations
from tools.normalize.core.normalization import RowSupport, StandardCsvWriter

import csv
from pathlib import Path

ROOT = Path.cwd()
RAW = ROOT / "data/raw"
OUT = ROOT / "data/normalized"
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

SAKADO = RAW / "11-埼玉県/11239-坂戸市/public-toilet/11239_public-toilet.csv"
OTSU = [
    ("parks", RAW / "25-滋賀県/25201-大津市/public-toilet/25201_parks_public-toilet.csv"),
    ("waste", RAW / "25-滋賀県/25201-大津市/public-toilet/25201_waste_public-toilet.csv"),
    ("tourism", RAW / "25-滋賀県/25201-大津市/public-toilet/25201_tourism_public-toilet.csv"),
]

LEGACY_MAP = {
    "名称": "名称",
    "名称_カナ": "名称_カナ",
    "名称_英語": "名称_英語",
    "住所": "所在地_連結表記",
    "方書": "建物名等(方書)",
    "設置位置": "設置位置",
    "緯度": "緯度",
    "経度": "経度",
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
    "利用開始時間": "利用開始時間",
    "利用終了時間": "利用終了時間",
    "利用可能時間特記事項": "利用可能時間特記事項",
    "画像": "画像",
    "画像_ライセンス": "画像_ライセンス",
    "備考": "備考",
}


def schema():
    with SCHEMA_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return [r["name"] for r in csv.DictReader(f)]


def detect_encoding(path):
    b = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            b.decode(enc)
            return enc
        except UnicodeDecodeError:
            pass
    raise RuntimeError(f"cannot decode: {path}")


def read_dicts(path):
    enc = detect_encoding(path)
    with path.open("r", encoding=enc, newline="") as f:
        r = csv.DictReader(f)
        rows = []
        for row in r:
            clean = {k: (v or "").strip() for k, v in row.items()}
            if any(clean.values()):
                rows.append(clean)
        return enc, r.fieldnames or [], rows


def normalize_sakado(fields):
    enc, header, rows = read_dicts(SAKADO)
    missing = [c for c in fields if c not in header]
    if missing:
        raise RuntimeError(f"坂戸市 missing columns: {missing}")

    extras = [c for c in header if c not in fields]
    if len(extras) != 11 or any(c != "" for c in extras):
        raise RuntimeError(f"坂戸市 unexpected extra columns: {extras!r}")

    out = []
    for src in rows:
        row = {c: src.get(c, "") for c in fields}
        for f in ("利用開始時間", "利用終了時間"):
            if row[f] == "なし":
                RowSupport.append_note(row, f"原データ{f}=なし")
                row[f] = ""
        out.append(row)

    dest = OUT / "11-埼玉県/11239-坂戸市/public-toilet/public-toilet.csv"
    return dest, out, enc


def normalize_otsu(fields):
    all_rows = []

    for source, path in OTSU:
        enc, header, rows = read_dicts(path)

        if source == "parks":
            missing = [c for c in fields if c not in header]
            if missing:
                raise RuntimeError(f"大津市 parks missing columns: {missing}")
            if [c for c in header if c not in fields] != ["男女共用トイレ数（小便器）"]:
                raise RuntimeError("大津市 parks unexpected schema")

            for src in rows:
                row = {c: src.get(c, "") for c in fields}
                extra = src.get("男女共用トイレ数（小便器）", "")
                if extra:
                    RowSupport.append_note(row, f"原データ男女共用トイレ数（小便器）={extra}")
                RowSupport.append_note(row, "出典区分=公園緑地課")
                all_rows.append(row)

        else:
            for src in rows:
                row = {c: "" for c in fields}
                for s, d in LEGACY_MAP.items():
                    row[d] = src.get(s, "")

                legacy_code = src.get("都道府県コード又は市区町村コード", "")
                if legacy_code:
                    row["全国地方公共団体コード"] = legacy_code
                    row["所在地_全国地方公共団体コード"] = legacy_code

                pref = src.get("都道府県名", "")
                city = src.get("市区町村名", "")
                if pref:
                    row["所在地_都道府県"] = pref
                if city:
                    row["地方公共団体名"] = f"{pref}{city}" if pref else city
                    row["所在地_市区町村"] = city

                no = src.get("NO", "")
                if no:
                    RowSupport.append_note(row, f"原データNO={no}")

                multi = src.get("多機能トイレ数", "")
                if multi:
                    RowSupport.append_note(row, f"原データ多機能トイレ数={multi}")

                RowSupport.append_note(
                    row,
                    "出典区分=" + ("廃棄物減量推進課" if source == "waste" else "観光振興課")
                )
                all_rows.append(row)

    expected_code = "252018"

    for row in all_rows:
        wheelchair = (
            row.get("車椅子使用者用トイレ有無") or ""
        ).strip()

        if wheelchair.isdigit():
            RowSupport.append_note(
                row,
                f"原データ車椅子使用者用トイレ有無={wheelchair}",
            )
            row["車椅子使用者用トイレ有無"] = (
                "無" if int(wheelchair) == 0 else "有"
            )

        if not (row.get("全国地方公共団体コード") or "").strip():
            row["全国地方公共団体コード"] = expected_code

        if not (
            row.get("所在地_全国地方公共団体コード") or ""
        ).strip():
            row["所在地_全国地方公共団体コード"] = expected_code


    dest = OUT / "25-滋賀県/25201-大津市/public-toilet/public-toilet.csv"
    return dest, all_rows


TARGETS = {
    "11239": "sakado",
    "25201": "otsu",
}


def main():
    fields = schema()
    if len(fields) != 39:
        raise RuntimeError(f"schema columns={len(fields)}")

    print(f"preflight OK: {len(TARGETS)} municipalities")
    if "11239" in TARGETS:
        sdest, srows, senc = normalize_sakado(fields)
        StandardCsvWriter().write(sdest, fields, srows)
        print(f"OK 坂戸市: rows={len(srows)} source_encoding={senc}")
    if "25201" in TARGETS:
        odest, orows = normalize_otsu(fields)
        StandardCsvWriter().write(odest, fields, orows)
        print(f"OK 大津市: rows={len(orows)} sources=3")


if __name__ == "__main__":
    main()
