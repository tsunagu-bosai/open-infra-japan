#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from tools.normalize.core.normalization import RowSupport, StandardCsvWriter
from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.encoding import detect_text_encoding

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "01229": {
        "pref": "01-北海道",
        "mun": "01229-富良野市",
        "name": "富良野市",
        "kind": "furano",
    },
    "05206": {
        "pref": "05-秋田県",
        "mun": "05206-男鹿市",
        "name": "男鹿市",
        "kind": "oga",
    },
    "15204": {
        "pref": "15-新潟県",
        "mun": "15204-三条市",
        "name": "三条市",
        "kind": "sanjo",
    },
    "16209": {
        "pref": "16-富山県",
        "mun": "16209-小矢部市",
        "name": "小矢部市",
        "kind": "oyabe",
    },
    "27140": {
        "pref": "27-大阪府",
        "mun": "27140-堺市",
        "name": "堺市",
        "kind": "sakai",
    },
}


def find_source(cfg):
    d = ROOT / "data/raw" / cfg["pref"] / cfg["mun"] / "public-toilet"
    files = sorted(d.glob("*.csv"))
    if len(files) != 1:
        raise RuntimeError(f"{cfg['mun']}: expected exactly 1 CSV, got {files!r}")
    return files[0]


def hhmm(v: str) -> str:
    v = (v or "").strip()
    if not v:
        return ""
    parts = v.split(":")
    if len(parts) == 2 and all(p.isdigit() for p in parts):
        h, m = map(int, parts)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return f"{h:02d}:{m:02d}"
    return v


def read_rows(path):
    enc = detect_text_encoding(path)
    with path.open("r", encoding=enc, newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        raise RuntimeError(f"empty: {path}")
    return enc, rows[0], rows[1:]


def copy_exact(clean, schema):
    row = {c: "" for c in schema}
    for c in schema:
        if c in clean:
            row[c] = clean[c]
    return row


def prepare_furano(code5, cfg, schema, header, data):
    expected = [
        "全国地方公共団体コード", "ID", "地方公共団体名", "名称", "名称_カナ",
        "名称_英語", "所在地_全国地方公共団体コード", "所在地_連結表記",
        "所在地_都道府県", "所在地_市区町村", "所在地_町字",
        "所在地_番地以下", "緯度", "経度",
    ]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    code6 = six_digit_municipality_code(code5)
    rows = []
    for line_no, values in enumerate(data, 2):
        if len(values) != len(header):
            raise RuntimeError(f"{code5}:{line_no}: bad column count")
        clean = {h: v.strip() for h, v in zip(header, values)}
        if clean["全国地方公共団体コード"] != code6:
            raise RuntimeError(f"{code5}:{line_no}: unexpected municipality code")
        if clean["所在地_全国地方公共団体コード"] != code6:
            raise RuntimeError(f"{code5}:{line_no}: unexpected location code")

        row = copy_exact(clean, schema)
        if row["地方公共団体名"] == "北海道富良野市":
            RowSupport.append_note(row, "原データ地方公共団体名=北海道富良野市")
            row["地方公共団体名"] = cfg["name"]
        rows.append(row)

    return rows, {"code": code6}


def prepare_oga(code5, cfg, schema, header, data):
    expected = [
        "名称", "名称_カナ", "所在地_連結表記", "設置位置",
        "バリアフリートイレ数", "車椅子使用者用トイレ有無",
        "乳幼児用設備設置トイレ有無", "オストメイト設置トイレ有無",
        "利用開始時間", "利用終了時間", "利用可能時間特記事項",
    ]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    code6 = six_digit_municipality_code(code5)
    rows = []
    corrected_end = 0

    for line_no, values in enumerate(data, 2):
        if len(values) != len(header):
            raise RuntimeError(f"{code5}:{line_no}: bad column count")
        clean = {h: v.strip() for h, v in zip(header, values)}
        row = copy_exact(clean, schema)

        row["全国地方公共団体コード"] = code6
        row["地方公共団体名"] = cfg["name"]

        if clean["利用開始時間"] != "0:00":
            raise RuntimeError(
                f"{code5}:{line_no}: unexpected start={clean['利用開始時間']!r}"
            )
        if clean["利用終了時間"] != "24:00:00":
            raise RuntimeError(
                f"{code5}:{line_no}: unexpected end={clean['利用終了時間']!r}"
            )

        row["利用開始時間"] = "00:00"
        row["利用終了時間"] = "23:59"
        RowSupport.append_note(row, "原データ利用終了時間=24:00:00")
        corrected_end += 1
        rows.append(row)

    return rows, {"code": code6, "end_time_corrected": corrected_end}


def prepare_sanjo(code5, cfg, schema, header, data):
    expected = ["category", "name", "latitude", "longitude", "address"]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    code6 = six_digit_municipality_code(code5)
    rows = []

    for line_no, values in enumerate(data, 2):
        if len(values) != 5:
            raise RuntimeError(f"{code5}:{line_no}: bad column count")
        clean = {h: v.strip() for h, v in zip(header, values)}

        row = {c: "" for c in schema}
        row["全国地方公共団体コード"] = code6
        row["地方公共団体名"] = cfg["name"]
        row["名称"] = clean["name"]
        row["所在地_連結表記"] = clean["address"]
        row["所在地_市区町村"] = cfg["name"]
        row["緯度"] = clean["latitude"]
        row["経度"] = clean["longitude"]
        RowSupport.append_note(row, f"原データcategory={clean['category']}")
        rows.append(row)

    return rows, {"code": code6, "category_preserved": len(rows)}


def prepare_oyabe(code5, cfg, schema, header, data):
    expected = [
        "項目", "都道府県コード又は市区町村コード", "NO", "都道府県名",
        "市区町村名", "名称", "名称_カナ", "住所", "設置位置", "緯度", "経度",
        "男性トイレ総数", "女性トイレ総数", "男女共用トイレ総数",
        "多機能トイレ数", "車椅子使用者用トイレ有無",
        "乳幼児用設備設置トイレ有無", "オストメイト設置トイレ有無",
        "利用可能時間特記事項",
    ]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    code6 = six_digit_municipality_code(code5)
    rows = []

    for line_no, values in enumerate(data, 2):
        if len(values) != len(header):
            raise RuntimeError(f"{code5}:{line_no}: bad column count")
        clean = {h: v.strip() for h, v in zip(header, values)}

        if clean["都道府県コード又は市区町村コード"] != code6:
            raise RuntimeError(f"{code5}:{line_no}: unexpected municipality code")
        if clean["項目"] != clean["NO"]:
            raise RuntimeError(
                f"{code5}:{line_no}: 項目/NO differ "
                f"{clean['項目']!r}/{clean['NO']!r}"
            )

        row = {c: "" for c in schema}
        row["全国地方公共団体コード"] = code6
        row["地方公共団体名"] = cfg["name"]
        row["ID"] = clean["NO"]
        row["所在地_都道府県"] = clean["都道府県名"]
        row["所在地_市区町村"] = clean["市区町村名"]
        row["所在地_連結表記"] = clean["住所"]
        row["名称"] = clean["名称"]
        row["名称_カナ"] = clean["名称_カナ"]
        row["設置位置"] = clean["設置位置"]
        row["緯度"] = clean["緯度"]
        row["経度"] = clean["経度"]
        row["男性トイレ総数"] = clean["男性トイレ総数"]
        row["女性トイレ総数"] = clean["女性トイレ総数"]
        row["男女共用トイレ総数"] = clean["男女共用トイレ総数"]
        row["車椅子使用者用トイレ有無"] = clean["車椅子使用者用トイレ有無"]
        row["乳幼児用設備設置トイレ有無"] = clean["乳幼児用設備設置トイレ有無"]
        row["オストメイト設置トイレ有無"] = clean["オストメイト設置トイレ有無"]
        row["利用可能時間特記事項"] = clean["利用可能時間特記事項"]

        RowSupport.append_note(row, f"原データ多機能トイレ数={clean['多機能トイレ数']}")
        rows.append(row)

    return rows, {"code": code6, "multifunction_preserved": len(rows)}


def prepare_sakai(code5, cfg, schema, header, data):
    expected = [
        "都道府県名", "市区町村名", "名称", "名称_カナ", "名称_英語",
        "住所", "設置位置", "緯度", "経度", "男性トイレ\r\n総数",
        "男性トイレ数\r\n（小便器）", "男性トイレ数\r\n（和式）",
        "男性トイレ数\r\n（洋式）", "女性トイレ\r\n総数",
        "女性トイレ数\r\n（和式）", "女性トイレ数\r\n（洋式）",
        "男女共用トイレ\r\n総数", "男女共用トイレ数\r\n（和式）",
        "男女共用トイレ数\r\n（洋式）", "多機能トイレ数",
        "車椅子使用者用\r\nトイレ有無", "乳幼児用設備\r\n設置トイレ有無",
        "オストメイト\r\n設置トイレ有無", "利用開始時間", "利用終了時間",
    ]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    code6 = six_digit_municipality_code(code5)
    aliases = {
        "男性トイレ\r\n総数": "男性トイレ総数",
        "男性トイレ数\r\n（小便器）": "男性トイレ数（小便器）",
        "男性トイレ数\r\n（和式）": "男性トイレ数（和式）",
        "男性トイレ数\r\n（洋式）": "男性トイレ数（洋式）",
        "女性トイレ\r\n総数": "女性トイレ総数",
        "女性トイレ数\r\n（和式）": "女性トイレ数（和式）",
        "女性トイレ数\r\n（洋式）": "女性トイレ数（洋式）",
        "男女共用トイレ\r\n総数": "男女共用トイレ総数",
        "男女共用トイレ数\r\n（和式）": "男女共用トイレ数（和式）",
        "男女共用トイレ数\r\n（洋式）": "男女共用トイレ数（洋式）",
        "車椅子使用者用\r\nトイレ有無": "車椅子使用者用トイレ有無",
        "乳幼児用設備\r\n設置トイレ有無": "乳幼児用設備設置トイレ有無",
        "オストメイト\r\n設置トイレ有無": "オストメイト設置トイレ有無",
    }

    rows = []
    for line_no, values in enumerate(data, 2):
        if len(values) != len(header):
            raise RuntimeError(f"{code5}:{line_no}: bad column count")
        clean = {
            h: "\n".join(part.strip() for part in v.splitlines()).strip()
            for h, v in zip(header, values)
        }
        row = {c: "" for c in schema}

        row["全国地方公共団体コード"] = code6
        row["地方公共団体名"] = cfg["name"]
        row["所在地_都道府県"] = clean["都道府県名"]
        row["所在地_市区町村"] = clean["市区町村名"]
        row["名称"] = clean["名称"]
        row["名称_カナ"] = clean["名称_カナ"]
        row["名称_英語"] = clean["名称_英語"]
        row["所在地_連結表記"] = clean["住所"]
        row["設置位置"] = clean["設置位置"]
        row["緯度"] = clean["緯度"]
        row["経度"] = clean["経度"]

        for old, new in aliases.items():
            row[new] = clean[old]

        row["利用開始時間"] = hhmm(clean["利用開始時間"])
        row["利用終了時間"] = hhmm(clean["利用終了時間"])
        RowSupport.append_note(row, f"原データ多機能トイレ数={clean['多機能トイレ数']}")
        rows.append(row)

    return rows, {"code": code6, "multifunction_preserved": len(rows)}


PREPARERS = {
    "furano": prepare_furano,
    "oga": prepare_oga,
    "sanjo": prepare_sanjo,
    "oyabe": prepare_oyabe,
    "sakai": prepare_sakai,
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
        rows, stats = PREPARERS[cfg["kind"]](
            code5, cfg, schema, header, data
        )


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
