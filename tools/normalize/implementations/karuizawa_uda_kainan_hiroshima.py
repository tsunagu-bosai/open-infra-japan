#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.normalization import RowSupport, StandardCsvWriter

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "20321": {
        "pref": "20-長野県", "mun": "20321-軽井沢町", "name": "軽井沢町",
        "file": "2535.csv", "encoding": "cp932",
        "kind": "karuizawa",
    },
    "29212": {
        "pref": "29-奈良県", "mun": "29212-宇陀市", "name": "宇陀市",
        "file": "3087.csv", "encoding": "cp932",
        "kind": "uda",
    },
    "30202": {
        "pref": "30-和歌山県", "mun": "30202-海南市", "name": "海南市",
        "file": "30202_public-toilet.csv", "encoding": "cp932",
        "kind": "kainan",
    },
    "34100": {
        "pref": "34-広島県", "mun": "34100-広島市", "name": "広島市",
        "file": "opendata_214.csv", "encoding": "utf-8-sig",
        "kind": "hiroshima",
    },
    "28585": {
        "pref": "28-兵庫県", "mun": "28585-香美町", "name": "香美町",
        "file": "kami_koushubenjo.csv", "encoding": "cp932",
        "kind": "kami",
    },
}



def read_rows(path, encoding):
    with path.open("r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or [], list(reader)


def prepare_karuizawa(code5, cfg, schema, header, srcrows):
    expected = ["資産名称", "大分類", "小分類", "所在地", "日本_60進_X", "日本_60進_Y"]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    out = []
    for line_no, s in enumerate(srcrows, 2):
        c = {k: (v or "").strip() for k, v in s.items()}
        lon = float(c["日本_60進_X"])
        lat = float(c["日本_60進_Y"])
        if not (130 <= lon <= 150 and 30 <= lat <= 46):
            raise RuntimeError(f"{code5}:{line_no}: unexpected coordinates {lon}/{lat}")

        row = {k: "" for k in schema}
        row["全国地方公共団体コード"] = six_digit_municipality_code(code5)
        row["地方公共団体名"] = cfg["name"]
        row["名称"] = c["資産名称"]
        row["所在地_連結表記"] = c["所在地"]
        row["所在地_都道府県"] = "長野県"
        row["所在地_市区町村"] = cfg["name"]
        row["緯度"] = c["日本_60進_Y"]
        row["経度"] = c["日本_60進_X"]
        RowSupport.append_note(row, f"原データ大分類={c['大分類']}")
        if c["小分類"]:
            RowSupport.append_note(row, f"原データ小分類={c['小分類']}")
        out.append(row)
    return out, {"blank_ids": len(out), "xy_mapped": len(out)}


def prepare_uda(code5, cfg, schema, header, srcrows):
    expected = ["区分", "No2", "地域", "施設名称", "詳細場所", "所在地", "施設電話番号", "緯度", "経度"]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    out = []
    blank_ids = 0
    for line_no, s in enumerate(srcrows, 2):
        c = {k: (v or "").strip() for k, v in s.items()}
        row = {k: "" for k in schema}
        row["全国地方公共団体コード"] = six_digit_municipality_code(code5)
        row["地方公共団体名"] = cfg["name"]
        row["ID"] = c["No2"]
        if not row["ID"]:
            blank_ids += 1
        row["名称"] = c["施設名称"]
        row["所在地_連結表記"] = c["所在地"]
        row["所在地_都道府県"] = "奈良県"
        row["所在地_市区町村"] = cfg["name"]
        row["設置位置"] = c["詳細場所"]
        row["緯度"] = c["緯度"]
        row["経度"] = c["経度"]
        RowSupport.append_note(row, f"原データ区分={c['区分']}")
        RowSupport.append_note(row, f"原データ地域={c['地域']}")
        if c["施設電話番号"]:
            RowSupport.append_note(row, f"原データ施設電話番号={c['施設電話番号']}")
        out.append(row)

    return out, {"blank_ids": blank_ids}


def prepare_kainan(code5, cfg, schema, header, srcrows):
    expected = ["市内公園等のトイレ情報", "住所"]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    out = []
    for s in srcrows:
        c = {k: (v or "").strip() for k, v in s.items()}
        row = {k: "" for k in schema}
        row["全国地方公共団体コード"] = six_digit_municipality_code(code5)
        row["地方公共団体名"] = cfg["name"]
        row["名称"] = c["市内公園等のトイレ情報"]
        row["所在地_連結表記"] = c["住所"]
        row["所在地_都道府県"] = "和歌山県"
        row["所在地_市区町村"] = cfg["name"]
        out.append(row)

    return out, {"blank_ids": len(out), "blank_coordinates": len(out)}


def prepare_hiroshima(code5, cfg, schema, header, srcrows):
    expected = ["名称", "名称かな", "所在地", "施設ID", "経度", "緯度", "分類"]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    out = []
    for line_no, s in enumerate(srcrows, 2):
        c = {k: (v or "").strip() for k, v in s.items()}
        lon = float(c["経度"])
        lat = float(c["緯度"])
        if not (130 <= lon <= 150 and 30 <= lat <= 46):
            raise RuntimeError(f"{code5}:{line_no}: unexpected coordinates {lon}/{lat}")

        row = {k: "" for k in schema}
        row["全国地方公共団体コード"] = six_digit_municipality_code(code5)
        row["地方公共団体名"] = cfg["name"]
        row["ID"] = c["施設ID"]
        row["名称"] = c["名称"]
        row["名称_カナ"] = c["名称かな"]
        row["所在地_連結表記"] = c["所在地"]
        row["所在地_都道府県"] = "広島県"
        row["所在地_市区町村"] = cfg["name"]
        row["緯度"] = c["緯度"]
        row["経度"] = c["経度"]
        RowSupport.append_note(row, f"原データ分類={c['分類']}")
        out.append(row)

    return out, {"classification_preserved": len(out)}


def prepare_kami(code5, cfg, schema, header, srcrows):
    expected = [
        "NO", "施設名", "整備年度", "延床面積(㎡)",
        "取得価額（千円）", "減価償却累計額（千円）", "資産減価償却率（％）",
    ]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    def value(text):
        cleaned = (text or "").strip()
        return "" if cleaned in {"-", "ー", "－", "―"} else cleaned

    out = []
    for line_no, s in enumerate(srcrows, 2):
        c = {k: value(v) for k, v in s.items()}
        ident = c["NO"]
        if not ident.isdigit():
            raise RuntimeError(f"{code5}:{line_no}: invalid NO={ident!r}")
        if not c["施設名"]:
            raise RuntimeError(f"{code5}:{line_no}: blank facility name")

        row = {k: "" for k in schema}
        row["全国地方公共団体コード"] = six_digit_municipality_code(code5)
        row["地方公共団体名"] = cfg["name"]
        row["ID"] = ident
        row["名称"] = c["施設名"]

        for field in (
            "整備年度",
            "延床面積(㎡)",
            "取得価額（千円）",
            "減価償却累計額（千円）",
            "資産減価償却率（％）",
        ):
            if c[field]:
                RowSupport.append_note(row, f"原データ{field}={c[field]}")

        out.append(row)

    return out, {"blank_coordinates": len(out), "asset_inventory_rows": len(out)}


PREP = {
    "karuizawa": prepare_karuizawa,
    "uda": prepare_uda,
    "kainan": prepare_kainan,
    "hiroshima": prepare_hiroshima,
    "kami": prepare_kami,
}



def main():
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    prepared = []
    for code5, cfg in TARGETS.items():
        src = ROOT / "data/raw" / cfg["pref"] / cfg["mun"] / "public-toilet" / cfg["file"]
        dest = ROOT / "data/normalized" / cfg["pref"] / cfg["mun"] / "public-toilet/public-toilet.csv"
        if not src.exists():
            raise RuntimeError(f"{code5}: missing source {src}")
        if dest.exists():
            raise RuntimeError(f"{code5}: normalized already exists {dest}")

        header, srcrows = read_rows(src, cfg["encoding"])

        rows, stats = PREP[cfg["kind"]](code5, cfg, schema, header, srcrows)

        ids = [r["ID"] for r in rows if r["ID"]]
        if len(ids) != len(set(ids)):
            raise RuntimeError(f"{code5}: duplicate nonblank IDs")

        prepared.append((code5, cfg, dest, rows, stats))

    print(f"preflight OK: {len(prepared)} municipalities")
    for code5, cfg, dest, rows, stats in prepared:
        StandardCsvWriter().write(dest, schema, rows)
        detail = " ".join(f"{k}={v}" for k, v in stats.items())
        print(
            f"OK {code5} {cfg['name']}: rows={len(rows)} "
            f"encoding={cfg['encoding']} code={six_digit_municipality_code(code5)} {detail}"
        )


if __name__ == "__main__":
    main()
