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
    "01202": {
        "pref": "01-北海道",
        "mun": "01202-函館市",
        "name": "函館市",
        "kind": "hakodate",
    },
    "02201": {
        "pref": "02-青森県",
        "mun": "02201-青森市",
        "name": "青森市",
        "kind": "aomori",
    },
    "05212": {
        "pref": "05-秋田県",
        "mun": "05212-大仙市",
        "name": "大仙市",
        "kind": "daisen",
    },
    "13228": {
        "pref": "13-東京都",
        "mun": "13228-あきる野市",
        "name": "あきる野市",
        "kind": "akiruno",
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


def prepare_hakodate(code5, cfg, schema, header, data):
    expected = [
        "No", "名称", "名称_カナ", "住所", "設置位置", "緯度", "経度",
        "男性トイレ総数", "女性トイレ総数", "男女共用トイレ総数",
        "多機能トイレ数", "車いす使用者用トイレ有無",
        "乳幼児用設備設置トイレ有無", "オストメイト設置トイレ有無",
        "利用開始時間", "利用終了時間", "備考",
    ]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    code6 = six_digit_municipality_code(code5)
    rows = []
    for line_no, values in enumerate(data, 2):
        if len(values) != len(header):
            raise RuntimeError(f"{code5}:{line_no}: bad column count")
        clean = {h: v.strip() for h, v in zip(header, values)}

        row = {c: "" for c in schema}
        row["全国地方公共団体コード"] = code6
        row["地方公共団体名"] = cfg["name"]
        row["ID"] = clean["No"]
        row["名称"] = clean["名称"]
        row["名称_カナ"] = clean["名称_カナ"]
        row["所在地_連結表記"] = clean["住所"]
        row["所在地_都道府県"] = "北海道"
        row["所在地_市区町村"] = cfg["name"]
        row["設置位置"] = clean["設置位置"]
        row["緯度"] = clean["緯度"]
        row["経度"] = clean["経度"]
        row["男性トイレ総数"] = clean["男性トイレ総数"]
        row["女性トイレ総数"] = clean["女性トイレ総数"]
        row["男女共用トイレ総数"] = clean["男女共用トイレ総数"]
        row["車椅子使用者用トイレ有無"] = clean["車いす使用者用トイレ有無"]
        row["乳幼児用設備設置トイレ有無"] = clean["乳幼児用設備設置トイレ有無"]
        row["オストメイト設置トイレ有無"] = clean["オストメイト設置トイレ有無"]
        row["利用開始時間"] = hhmm(clean["利用開始時間"])
        row["利用終了時間"] = hhmm(clean["利用終了時間"])
        row["備考"] = clean["備考"]
        RowSupport.append_note(row, f"原データ多機能トイレ数={clean['多機能トイレ数']}")
        rows.append(row)

    return rows, {"code": code6, "multifunction_preserved": len(rows)}


def prepare_aomori(code5, cfg, schema, header, data):
    expected = [
        "都道府県コード又は市区町村コード", "NO", "都道府県名", "市区町村名",
        "名称", "名称_カナ", "住所", "設置位置", "緯度", "経度",
        "男性トイレ総数", "男性トイレ数（小便器）", "男性トイレ数（和式）",
        "男性トイレ数（洋式）", "女性トイレ総数", "女性トイレ数（和式）",
        "女性トイレ数（洋式）", "男女共用トイレ総数",
        "男女共用トイレ数（和式）", "男女共用トイレ数（洋式）",
        "多機能トイレ数", "車椅子使用者用トイレ有無",
        "乳幼児用設備設置トイレ有無", "オストメイト設置トイレ有無",
        "利用可能時間", "備考", "担当課",
    ]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    code6 = six_digit_municipality_code(code5)
    rows = []
    dropped_empty = 0
    corrected_code = 0

    for line_no, values in enumerate(data, 2):
        if len(values) != len(header):
            raise RuntimeError(f"{code5}:{line_no}: bad column count")
        clean = {h: v.strip() for h, v in zip(header, values)}
        if not any(clean.values()):
            dropped_empty += 1
            continue

        if clean["都道府県コード又は市区町村コード"] != "22012":
            raise RuntimeError(
                f"{code5}:{line_no}: unexpected source code="
                f"{clean['都道府県コード又は市区町村コード']!r}"
            )

        row = {c: "" for c in schema}
        row["全国地方公共団体コード"] = code6
        row["地方公共団体名"] = cfg["name"]
        row["ID"] = clean["NO"]
        row["所在地_都道府県"] = clean["都道府県名"]
        row["所在地_市区町村"] = clean["市区町村名"]
        row["名称"] = clean["名称"]
        row["名称_カナ"] = clean["名称_カナ"]
        row["所在地_連結表記"] = clean["住所"]
        row["設置位置"] = clean["設置位置"]
        row["緯度"] = clean["緯度"]
        row["経度"] = clean["経度"]

        for c in (
            "男性トイレ総数", "男性トイレ数（小便器）", "男性トイレ数（和式）",
            "男性トイレ数（洋式）", "女性トイレ総数", "女性トイレ数（和式）",
            "女性トイレ数（洋式）", "男女共用トイレ総数",
            "男女共用トイレ数（和式）", "男女共用トイレ数（洋式）",
            "車椅子使用者用トイレ有無", "乳幼児用設備設置トイレ有無",
            "オストメイト設置トイレ有無",
        ):
            row[c] = clean[c]

        row["利用可能時間特記事項"] = clean["利用可能時間"]
        row["備考"] = clean["備考"]
        RowSupport.append_note(row, "原データ全国地方公共団体コード=22012")
        RowSupport.append_note(row, f"原データ多機能トイレ数={clean['多機能トイレ数']}")
        if clean["担当課"]:
            RowSupport.append_note(row, f"原データ担当課={clean['担当課']}")
        corrected_code += 1
        rows.append(row)

    return rows, {
        "code": code6,
        "code_corrected": corrected_code,
        "empty_rows_dropped": dropped_empty,
    }


def prepare_daisen(code5, cfg, schema, header, data):
    expected = [
        "市町村コード", "ＮＯ", "都道府県", "市町村名", "名称", "名称＿カナ",
        "名称＿英語", "住所", "方書", "設置位置", "所管課", "有無", "緯度",
        "経度", "男性トイレ数", "男性トイレ数（小便器）",
        "男性トイレ数（和式）", "男性トイレ数（洋式）", "女性トイレ数",
        "女性トイレ数（小便器）", "女性トイレ数（和式）",
        "女性トイレ数（洋式）", "男女共用トイレ数",
        "男女共用トイレ数（和式）", "男女共用トイレ数（洋式）",
        "多機能トイレ数", "車いす使用者用トイレ有無",
        "乳幼児用設備設置トイレ有無", "オストメイト設置トイレ有無",
        "利用開始時間", "利用終了時間", "利用可能時間特記事項",
        "画像", "画像ライセンス", "備考",
    ]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    code6 = six_digit_municipality_code(code5)
    rows = []
    for line_no, values in enumerate(data, 2):
        if len(values) != len(header):
            raise RuntimeError(f"{code5}:{line_no}: bad column count")
        clean = {h: v.strip() for h, v in zip(header, values)}

        if clean["市町村コード"] != code6:
            raise RuntimeError(
                f"{code5}:{line_no}: unexpected code={clean['市町村コード']!r}"
            )

        row = {c: "" for c in schema}
        row["全国地方公共団体コード"] = code6
        row["地方公共団体名"] = cfg["name"]
        row["ID"] = clean["ＮＯ"]
        row["名称"] = clean["名称"]
        row["名称_カナ"] = clean["名称＿カナ"]
        row["名称_英語"] = clean["名称＿英語"]
        row["所在地_連結表記"] = clean["住所"]
        row["所在地_都道府県"] = clean["都道府県"]
        row["所在地_市区町村"] = clean["市町村名"]
        row["建物名等(方書)"] = clean["方書"]
        row["設置位置"] = clean["設置位置"]
        row["緯度"] = clean["緯度"]
        row["経度"] = clean["経度"]
        row["男性トイレ総数"] = clean["男性トイレ数"]
        row["男性トイレ数（小便器）"] = clean["男性トイレ数（小便器）"]
        row["男性トイレ数（和式）"] = clean["男性トイレ数（和式）"]
        row["男性トイレ数（洋式）"] = clean["男性トイレ数（洋式）"]
        row["女性トイレ総数"] = clean["女性トイレ数"]
        row["女性トイレ数（和式）"] = clean["女性トイレ数（和式）"]
        row["女性トイレ数（洋式）"] = clean["女性トイレ数（洋式）"]
        row["男女共用トイレ総数"] = clean["男女共用トイレ数"]
        row["男女共用トイレ数（和式）"] = clean["男女共用トイレ数（和式）"]
        row["男女共用トイレ数（洋式）"] = clean["男女共用トイレ数（洋式）"]
        row["車椅子使用者用トイレ有無"] = clean["車いす使用者用トイレ有無"]
        row["乳幼児用設備設置トイレ有無"] = clean["乳幼児用設備設置トイレ有無"]
        row["オストメイト設置トイレ有無"] = clean["オストメイト設置トイレ有無"]
        row["利用開始時間"] = hhmm(clean["利用開始時間"])
        row["利用終了時間"] = hhmm(clean["利用終了時間"])
        row["利用可能時間特記事項"] = clean["利用可能時間特記事項"]
        row["画像"] = clean["画像"]
        row["画像_ライセンス"] = clean["画像ライセンス"]
        row["備考"] = clean["備考"]

        if clean["所管課"]:
            RowSupport.append_note(row, f"原データ所管課={clean['所管課']}")
        if clean["有無"]:
            RowSupport.append_note(row, f"原データ有無={clean['有無']}")
        if clean["女性トイレ数（小便器）"]:
            RowSupport.append_note(
                row,
                f"原データ女性トイレ数（小便器）={clean['女性トイレ数（小便器）']}",
            )
        if clean["多機能トイレ数"]:
            RowSupport.append_note(row, f"原データ多機能トイレ数={clean['多機能トイレ数']}")

        rows.append(row)

    return rows, {"code": code6}


def prepare_akiruno(code5, cfg, schema, header, data):
    expected = [
        "市区町村コード", "NO", "都道府県名", "市区町村名", "名称", "名称_カナ",
        "住所", "緯度", "経度", "男性トイレ_総数", "男性トイレ_（小便器）",
        "男性トイレ_（和式）", "男性トイレ_（洋式）", "女性トイレ_総数",
        "女性トイレ_（和式）", "女性トイレ_（洋式）",
        "男女共用トイレ_総数", "男女共用トイレ_（和式）",
        "男女共用トイレ_（洋式）", "多機能トイレ_数",
    ]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    code6 = six_digit_municipality_code(code5)
    rows = []
    dropped_empty = 0

    aliases = {
        "男性トイレ_総数": "男性トイレ総数",
        "男性トイレ_（小便器）": "男性トイレ数（小便器）",
        "男性トイレ_（和式）": "男性トイレ数（和式）",
        "男性トイレ_（洋式）": "男性トイレ数（洋式）",
        "女性トイレ_総数": "女性トイレ総数",
        "女性トイレ_（和式）": "女性トイレ数（和式）",
        "女性トイレ_（洋式）": "女性トイレ数（洋式）",
        "男女共用トイレ_総数": "男女共用トイレ総数",
        "男女共用トイレ_（和式）": "男女共用トイレ数（和式）",
        "男女共用トイレ_（洋式）": "男女共用トイレ数（洋式）",
    }

    for line_no, values in enumerate(data, 2):
        if len(values) != len(header):
            raise RuntimeError(f"{code5}:{line_no}: bad column count")
        clean = {h: v.strip() for h, v in zip(header, values)}
        if not any(clean.values()):
            dropped_empty += 1
            continue

        if clean["市区町村コード"] != code6:
            raise RuntimeError(
                f"{code5}:{line_no}: unexpected code={clean['市区町村コード']!r}"
            )

        row = {c: "" for c in schema}
        row["全国地方公共団体コード"] = code6
        row["地方公共団体名"] = cfg["name"]
        row["ID"] = clean["NO"]
        row["所在地_都道府県"] = clean["都道府県名"]
        row["所在地_市区町村"] = clean["市区町村名"]
        row["名称"] = clean["名称"]
        row["名称_カナ"] = clean["名称_カナ"]
        row["所在地_連結表記"] = clean["住所"]
        row["緯度"] = clean["緯度"]
        row["経度"] = clean["経度"]

        for old, new in aliases.items():
            row[new] = clean[old]

        RowSupport.append_note(row, f"原データ多機能トイレ数={clean['多機能トイレ_数']}")
        rows.append(row)


    return rows, {"code": code6, "empty_rows_dropped": dropped_empty}


PREPARERS = {
    "hakodate": prepare_hakodate,
    "aomori": prepare_aomori,
    "daisen": prepare_daisen,
    "akiruno": prepare_akiruno,
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
