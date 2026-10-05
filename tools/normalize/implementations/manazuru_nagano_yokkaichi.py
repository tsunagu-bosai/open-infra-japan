#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.normalization import RowSupport, StandardCsvWriter
from tools.normalize.core.encoding import detect_text_encoding

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "14383": {
        "pref": "14-神奈川県",
        "mun": "14383-真鶴町",
        "name": "真鶴町",
        "kind": "manazuru",
    },
    "20201": {
        "pref": "20-長野県",
        "mun": "20201-長野市",
        "name": "長野市",
        "kind": "nagano",
    },
    "24202": {
        "pref": "24-三重県",
        "mun": "24202-四日市市",
        "name": "四日市市",
        "kind": "yokkaichi",
    },
}


def find_source(cfg):
    d = ROOT / "data/raw" / cfg["pref"] / cfg["mun"] / "public-toilet"
    files = sorted(d.glob("*.csv"))
    if len(files) != 1:
        raise RuntimeError(f"{cfg['mun']}: expected exactly 1 CSV, got {files!r}")
    return files[0]



def append_time_note(row, text):
    text = (text or "").strip()
    if not text:
        return
    cur = (row.get("利用可能時間特記事項") or "").strip()
    if text in cur:
        return
    row["利用可能時間特記事項"] = f"{cur} / {text}" if cur else text


def read_rows(path):
    enc = detect_text_encoding(path)
    with path.open("r", encoding=enc, newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        raise RuntimeError(f"empty: {path}")
    return enc, rows[0], rows[1:]


def prepare_manazuru(code5, cfg, schema, header, data):
    expected = [
        "ID", "名称", "設置者", "種別", "提供時間制限有無", "提供時間",
        "男子小便器数", "男子大便器数", "女子便器数", "男女共用便器数",
        "だれでもトイレ室数", "住所1", "住所2", "緯度", "経度", "備考",
    ]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    code6 = six_digit_municipality_code(code5)
    rows = []
    for line_no, values in enumerate(data, 2):
        if len(values) != len(header):
            raise RuntimeError(f"{code5}:{line_no}: bad column count")
        c = {h: v.strip() for h, v in zip(header, values)}

        row = {k: "" for k in schema}
        row["全国地方公共団体コード"] = code6
        row["地方公共団体名"] = cfg["name"]
        row["ID"] = c["ID"]
        row["名称"] = c["名称"]
        row["所在地_連結表記"] = f"{c['住所1']}{c['住所2']}"
        row["所在地_都道府県"] = "神奈川県"
        row["所在地_市区町村"] = cfg["name"]
        row["所在地_町字"] = c["住所2"]
        row["緯度"] = c["緯度"]
        row["経度"] = c["経度"]
        row["男女共用トイレ総数"] = c["男女共用便器数"]
        row["男性トイレ数（小便器）"] = c["男子小便器数"]
        row["備考"] = c["備考"]

        append_time_note(row, c["提供時間"])
        RowSupport.append_note(row, f"原データ設置者={c['設置者']}")
        RowSupport.append_note(row, f"原データ種別={c['種別']}")
        RowSupport.append_note(row, f"原データ提供時間制限有無={c['提供時間制限有無']}")
        RowSupport.append_note(row, f"原データ男子大便器数={c['男子大便器数']}")
        RowSupport.append_note(row, f"原データ女子便器数={c['女子便器数']}")
        RowSupport.append_note(row, f"原データだれでもトイレ室数={c['だれでもトイレ室数']}")
        rows.append(row)

    return rows, {"code": code6, "custom_semantics_preserved": len(rows)}


def prepare_nagano(code5, cfg, schema, header, data):
    expected = [
        "public_toilet_202401", "名称", "大字町丁名", "番地", "号", "方書",
        "カナ", "英語名", "英語住所", "緯度", "経度",
    ]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    code6 = six_digit_municipality_code(code5)
    rows = []
    swapped = 0

    for line_no, values in enumerate(data, 2):
        if len(values) != len(header):
            raise RuntimeError(f"{code5}:{line_no}: bad column count")
        c = {h: v.strip() for h, v in zip(header, values)}

        raw_lat = float(c["緯度"])
        raw_lon = float(c["経度"])
        if not (130 <= raw_lat <= 150 and 30 <= raw_lon <= 46):
            raise RuntimeError(
                f"{code5}:{line_no}: unexpected coordinate pattern "
                f"{raw_lat}/{raw_lon}"
            )

        row = {k: "" for k in schema}
        row["全国地方公共団体コード"] = code6
        row["地方公共団体名"] = cfg["name"]
        row["ID"] = c["public_toilet_202401"]
        row["名称"] = c["名称"]
        row["名称_カナ"] = c["カナ"]
        row["名称_英語"] = c["英語名"]
        row["所在地_都道府県"] = "長野県"
        row["所在地_市区町村"] = cfg["name"]
        row["所在地_町字"] = c["大字町丁名"]

        ban = c["番地"]
        gou = c["号"]
        banchi = ban + (f"-{gou}" if gou else "")
        row["所在地_番地以下"] = banchi
        row["建物名等(方書)"] = c["方書"]
        row["所在地_連結表記"] = f"{cfg['name']}{c['大字町丁名']}{banchi}{c['方書']}"

        # Source columns are reversed: "緯度" contains longitude and vice versa.
        row["緯度"] = c["経度"]
        row["経度"] = c["緯度"]
        RowSupport.append_note(row, f"原データ緯度={c['緯度']}")
        RowSupport.append_note(row, f"原データ経度={c['経度']}")
        RowSupport.append_note(row, f"原データ英語住所={c['英語住所']}")
        swapped += 1
        rows.append(row)

    return rows, {"code": code6, "coordinates_swapped": swapped}


def prepare_yokkaichi(code5, cfg, schema, header, data):
    expected = [
        "全国地方公共団体コード", "ID", "所管課", "名称", "名称_カナ", "名称_英語",
        "所在地_連結表記", "設置位置", "男女共用トイレ総数", "和式便器数",
        "洋式便器数", "多目的便所数", "バリアフリートイレ数",
        "車椅子使用者用トイレ有無", "乳幼児用設備設置トイレ有無",
        "オストメイト設置トイレ有無", "備考", "緯度", "経度",
    ]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    code6 = six_digit_municipality_code(code5)
    rows = []

    for line_no, values in enumerate(data, 2):
        if len(values) != len(header):
            raise RuntimeError(f"{code5}:{line_no}: bad column count")
        c = {h: v.strip() for h, v in zip(header, values)}

        if c["全国地方公共団体コード"] != code6:
            raise RuntimeError(
                f"{code5}:{line_no}: unexpected code={c['全国地方公共団体コード']!r}"
            )

        row = {k: "" for k in schema}
        for k in (
            "全国地方公共団体コード", "ID", "名称", "名称_カナ", "名称_英語",
            "所在地_連結表記", "設置位置", "男女共用トイレ総数",
            "バリアフリートイレ数", "車椅子使用者用トイレ有無",
            "乳幼児用設備設置トイレ有無", "オストメイト設置トイレ有無",
            "備考", "緯度", "経度",
        ):
            row[k] = c[k]

        row["備考"] = (
            row["備考"]
            .replace("\r\n", " / ")
            .replace("\r", " / ")
            .replace("\n", " / ")
        )

        row["地方公共団体名"] = cfg["name"]
        row["所在地_都道府県"] = "三重県"
        row["所在地_市区町村"] = cfg["name"]

        RowSupport.append_note(row, f"原データ所管課={c['所管課']}")
        RowSupport.append_note(row, f"原データ和式便器数={c['和式便器数']}")
        RowSupport.append_note(row, f"原データ洋式便器数={c['洋式便器数']}")
        RowSupport.append_note(row, f"原データ多目的便所数={c['多目的便所数']}")
        row["バリアフリートイレ数"] = c["多目的便所数"]
        rows.append(row)

    return rows, {"code": code6, "multipurpose_preserved": len(rows)}


PREPARERS = {
    "manazuru": prepare_manazuru,
    "nagano": prepare_nagano,
    "yokkaichi": prepare_yokkaichi,
}



def main():
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    prepared = []
    for code5, cfg in TARGETS.items():
        src = find_source(cfg)
        dest = (
            ROOT / "data/normalized" / cfg["pref"] / cfg["mun"]
            / "public-toilet/public-toilet.csv"
        )
        if dest.exists():
            raise RuntimeError(f"{code5}: normalized already exists: {dest}")

        enc, header, data = read_rows(src)
        rows, stats = PREPARERS[cfg["kind"]](code5, cfg, schema, header, data)

        ids = [r["ID"] for r in rows if r["ID"]]
        if len(ids) != len(set(ids)):
            raise RuntimeError(f"{code5}: duplicate nonblank IDs")

        prepared.append((code5, cfg, dest, enc, rows, stats))

    print(f"preflight OK: {len(prepared)} municipalities")
    for code5, cfg, dest, enc, rows, stats in prepared:
        StandardCsvWriter().write(dest, schema, rows)
        detail = " ".join(f"{k}={v}" for k, v in stats.items())
        print(
            f"OK {code5} {cfg['name']}: rows={len(rows)} "
            f"encoding={enc} {detail}"
        )


if __name__ == "__main__":
    main()
