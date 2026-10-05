#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.encoding import detect_text_encoding
from tools.normalize.core.normalization import RowSupport, StandardCsvWriter

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "02210": {
        "pref": "02-青森県",
        "mun": "02210-平川市",
        "file": "02210_public-toilet.csv",
        "name": "平川市",
        "kind": "hirakawa",
    },
    "16206": {
        "pref": "16-富山県",
        "mun": "16206-滑川市",
        "file": "08_162060_public_toilet.csv",
        "name": "滑川市",
        "kind": "namerikawa",
    },
}


def append_time_note(row, text):
    text = (text or "").strip()
    if not text:
        return
    cur = (row.get("利用可能時間特記事項") or "").strip()
    if text in cur:
        return
    row["利用可能時間特記事項"] = f"{cur} / {text}" if cur else text


def hhmm(v: str) -> str:
    v = (v or "").strip()
    if not v:
        return ""
    parts = v.split(":")
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        h, m = int(parts[0]), int(parts[1])
        if 0 <= h <= 23 and 0 <= m <= 59:
            return f"{h:02d}:{m:02d}"
    return v


def read_positional(path: Path):
    enc = detect_text_encoding(path)
    with path.open("r", encoding=enc, newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        raise RuntimeError(f"empty: {path}")
    return enc, rows[0], rows[1:]


def prepare_hirakawa(code, cfg, schema, header, physical_rows):
    expected = [
        "都道府県コード又は市区町村コード", "NO", "都道府県名", "市区町村名",
        "名称", "名称_カナ", "名称_英語", "住所", "方書", "設置位置",
        "緯度", "経度", "男性トイレ総数", "男性トイレ数（小便器）",
        "男性トイレ数（和式）", "男性トイレ数（洋式）", "女性トイレ総数",
        "女性トイレ数（和式）", "女性トイレ数（洋式）", "男女共用トイレ総数",
        "男女共用トイレ数（和式）", "男女共用トイレ数（洋式）",
        "多機能トイレ数", "車椅子使用者用トイレ有無",
        "乳幼児用設備設置トイレ有無", "オストメイト設置トイレ有無",
        "利用開始時間", "利用終了時間", "利用可能時間特記事項",
        "画像", "画像_ライセンス", "備考", ""
    ]
    if header != expected:
        raise RuntimeError(f"{code}: source header drift")

    indexes = {h: i for i, h in enumerate(header) if h}
    blank_i = 32
    aliases = {
        "NO": "ID",
        "都道府県名": "所在地_都道府県",
        "市区町村名": "所在地_市区町村",
        "住所": "所在地_連結表記",
        "方書": "建物名等(方書)",
    }

    rows = []
    extra_added = 0
    raw_code_corrected = 0

    for line_no, src in enumerate(physical_rows, 2):
        if len(src) != 33:
            raise RuntimeError(f"{code}:{line_no}: columns={len(src)} expected=33")

        clean = {h: src[i].strip() for h, i in indexes.items()}
        if not any(v for v in clean.values()) and not src[blank_i].strip():
            continue

        if clean["都道府県コード又は市区町村コード"] != "22101":
            raise RuntimeError(
                f"{code}:{line_no}: unexpected raw municipality code="
                f"{clean['都道府県コード又は市区町村コード']!r}"
            )

        row = {c: clean.get(c, "") for c in schema}
        for old, new in aliases.items():
            row[new] = clean.get(old, "")

        row["全国地方公共団体コード"] = "022101"
        row["地方公共団体名"] = cfg["name"]
        RowSupport.append_note(row, "原データ全国地方公共団体コード=22101")
        raw_code_corrected += 1

        multif = clean.get("多機能トイレ数", "")
        if multif:
            RowSupport.append_note(row, f"原データ多機能トイレ数={multif}")

        extra = src[blank_i].strip()
        if extra:
            if extra != "追加":
                raise RuntimeError(
                    f"{code}:{line_no}: unexpected unnamed trailing value={extra!r}"
                )
            RowSupport.append_note(row, "原データ末尾無名列=追加")
            extra_added += 1

        row["利用開始時間"] = hhmm(clean.get("利用開始時間", ""))
        row["利用終了時間"] = hhmm(clean.get("利用終了時間", ""))
        rows.append(row)


    return rows, {
        "code_corrected": raw_code_corrected,
        "trailing_extra_preserved": extra_added,
    }


def prepare_namerikawa(code, cfg, schema, header, physical_rows):
    expected = [
        "都道府県\nコード又は\n市区町村\nコード", "NO", "都道府県名",
        "市区町村名", "名称", "名称_カナ", "名称_英語", "住所", "方書",
        "設置位置", "緯度", "経度", "男性トイレ総数",
        "男性トイレ数\n（小便器）", "男性トイレ数\n（和式）",
        "男性トイレ数\n（洋式）", "女性トイレ総数",
        "女性トイレ数\n（和式）", "女性トイレ数\n（洋式）",
        "男女共用トイレ総数", "男女共用トイレ数（和式）",
        "男女共用トイレ数（洋式）", "多機能トイレ数",
        "車椅子使用者\n用トイレ有無", "乳幼児用設備設\n置トイレ有無",
        "オストメイト\n設置トイレ有無", "利用開始時間", "利用終了時間",
        "利用可能時間\n特記事項", "画像", "画像_\nライセンス", "備考"
    ]
    if header != expected:
        raise RuntimeError(f"{code}: source header drift")

    indexes = {h: i for i, h in enumerate(header)}
    aliases = {
        "NO": "ID",
        "都道府県名": "所在地_都道府県",
        "市区町村名": "所在地_市区町村",
        "住所": "所在地_連結表記",
        "方書": "建物名等(方書)",
        "男性トイレ数\n（小便器）": "男性トイレ数（小便器）",
        "男性トイレ数\n（和式）": "男性トイレ数（和式）",
        "男性トイレ数\n（洋式）": "男性トイレ数（洋式）",
        "女性トイレ数\n（和式）": "女性トイレ数（和式）",
        "女性トイレ数\n（洋式）": "女性トイレ数（洋式）",
        "車椅子使用者\n用トイレ有無": "車椅子使用者用トイレ有無",
        "乳幼児用設備設\n置トイレ有無": "乳幼児用設備設置トイレ有無",
        "オストメイト\n設置トイレ有無": "オストメイト設置トイレ有無",
        "利用可能時間\n特記事項": "利用可能時間特記事項",
        "画像_\nライセンス": "画像_ライセンス",
    }

    rows = []
    no_holiday_rows = 0
    range_rows = 0
    code_corrected = 0

    for line_no, src in enumerate(physical_rows, 2):
        if len(src) != 32:
            raise RuntimeError(f"{code}:{line_no}: columns={len(src)} expected=32")

        clean = {h: src[i].strip() for h, i in indexes.items()}
        if not any(clean.values()):
            continue

        raw_code = clean["都道府県\nコード又は\n市区町村\nコード"]
        if raw_code != "16206":
            raise RuntimeError(
                f"{code}:{line_no}: unexpected raw municipality code={raw_code!r}"
            )

        row = {c: "" for c in schema}
        for c in schema:
            if c in clean:
                v = clean[c]
                row[c] = "" if v == "－" else v

        for old, new in aliases.items():
            v = clean.get(old, "")
            row[new] = "" if v == "－" else v

        row["全国地方公共団体コード"] = "162060"
        row["地方公共団体名"] = cfg["name"]
        RowSupport.append_note(row, "原データ全国地方公共団体コード=16206")
        code_corrected += 1

        multif = clean.get("多機能トイレ数", "")
        if multif:
            RowSupport.append_note(row, f"原データ多機能トイレ数={multif}")

        raw_start = clean.get("利用開始時間", "")
        raw_end = clean.get("利用終了時間", "")

        if raw_start == "無休" and raw_end == "無休":
            row["利用開始時間"] = ""
            row["利用終了時間"] = ""
            append_time_note(row, "無休")
            RowSupport.append_note(row, "原データ利用開始時間=無休")
            RowSupport.append_note(row, "原データ利用終了時間=無休")
            no_holiday_rows += 1
        elif raw_start == "9:00" and raw_end == "9:00～17:00":
            row["利用開始時間"] = "09:00"
            row["利用終了時間"] = "17:00"
            RowSupport.append_note(row, "原データ利用終了時間=9:00～17:00")
            range_rows += 1
        else:
            raise RuntimeError(
                f"{code}:{line_no}: unexpected time pair {raw_start!r}/{raw_end!r}"
            )

        if row.get("画像") == "－":
            row["画像"] = ""
        if row.get("画像_ライセンス") == "－":
            row["画像_ライセンス"] = ""
        if row.get("備考") == "－":
            row["備考"] = ""

        rows.append(row)


    return rows, {
        "code_corrected": code_corrected,
        "no_holiday_rows": no_holiday_rows,
        "parsed_range_rows": range_rows,
    }


def prepare_one(code, cfg, schema):
    src = ROOT / "data/raw" / cfg["pref"] / cfg["mun"] / "public-toilet" / cfg["file"]
    dest = ROOT / "data/normalized" / cfg["pref"] / cfg["mun"] / "public-toilet/public-toilet.csv"

    if not src.exists():
        raise RuntimeError(f"{code}: raw missing: {src}")
    if dest.exists():
        raise RuntimeError(f"{code}: normalized already exists: {dest}")

    enc, header, physical_rows = read_positional(src)

    if cfg["kind"] == "hirakawa":
        rows, stats = prepare_hirakawa(code, cfg, schema, header, physical_rows)
    elif cfg["kind"] == "namerikawa":
        rows, stats = prepare_namerikawa(code, cfg, schema, header, physical_rows)
    else:
        raise RuntimeError(f"unknown kind: {cfg['kind']}")

    if not rows:
        raise RuntimeError(f"{code}: no active source rows")

    ids = [r["ID"] for r in rows if r["ID"]]
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"{code}: duplicate nonblank IDs after mapping")

    return dest, enc, rows, stats


def main():
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    prepared = []
    for code, cfg in TARGETS.items():
        dest, enc, rows, stats = prepare_one(code, cfg, schema)
        prepared.append((code, cfg, dest, enc, rows, stats))

    print(f"preflight OK: {len(prepared)} municipalities")

    for code, cfg, dest, enc, rows, stats in prepared:
        StandardCsvWriter().write(dest, schema, rows)
        detail = " ".join(f"{k}={v}" for k, v in stats.items())
        print(f"OK {code} {cfg['name']}: rows={len(rows)} encoding={enc} {detail}")


if __name__ == "__main__":
    main()
