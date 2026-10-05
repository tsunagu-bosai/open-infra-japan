#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.normalization import RowSupport, StandardCsvWriter
from tools.normalize.core.encoding import detect_text_encoding

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "05202": {
        "pref": "05-秋田県",
        "mun": "05202-能代市",
        "file": "052027_public_toilet.csv",
        "name": "能代市",
        "kind": "noshiro",
    },
    "08233": {
        "pref": "08-茨城県",
        "mun": "08233-行方市",
        "file": "08233_public-toilet.csv",
        "name": "行方市",
        "kind": "namegata",
    },
    "13110": {
        "pref": "13-東京都",
        "mun": "13110-目黒区",
        "file": "13110_public-toilet.csv",
        "name": "目黒区",
        "kind": "meguro",
    },
}



def read_positional(path: Path):
    enc = detect_text_encoding(path)
    with path.open("r", encoding=enc, newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        raise RuntimeError(f"empty: {path}")
    return enc, rows[0], rows[1:]


def one_index(header, field):
    idxs = [i for i, h in enumerate(header) if h == field]
    if len(idxs) != 1:
        raise RuntimeError(f"field {field!r} occurs {len(idxs)} times")
    return idxs[0]


def prepare_noshiro(code, cfg, schema, header, physical_rows):
    aliases = {
        "所在地＿全国地方公共団体コード": "所在地_全国地方公共団体コード",
        "所在地＿連結表記": "所在地_連結表記",
        "所在地＿都道府県": "所在地_都道府県",
        "所在地＿市区町村": "所在地_市区町村",
        "所在地＿町字": "所在地_町字",
        "所在地＿番地以下": "所在地_番地以下",
        "建物名等（方書）": "建物名等(方書)",
        "高度の域": "高度の値",
    }

    indexes = {h: i for i, h in enumerate(header) if h}
    if len(indexes) != len([h for h in header if h]):
        raise RuntimeError(f"{code}: unexpected duplicate nonblank headers")

    # trailing blank spreadsheet column must be empty
    for i, h in enumerate(header):
        if h == "":
            for line_no, r in enumerate(physical_rows, 2):
                v = (r[i] if i < len(r) else "").strip()
                if v:
                    raise RuntimeError(
                        f"{code}:{line_no}: blank-header column contains {v!r}"
                    )

    rows = []
    for line_no, srcrow in enumerate(physical_rows, 2):
        clean = {
            h: (srcrow[i] if i < len(srcrow) else "").strip()
            for h, i in indexes.items()
        }
        if not any(clean.values()):
            continue

        row = {c: clean.get(c, "") for c in schema}
        for old, new in aliases.items():
            if old not in clean:
                raise RuntimeError(f"{code}: missing alias source {old!r}")
            row[new] = clean[old]

        if clean.get("多機能トイレ数"):
            RowSupport.append_note(row, f"原データ多機能トイレ数={clean['多機能トイレ数']}")

        # Source municipality name is "秋田県能代市"; standard municipality name
        # should be the municipality itself.
        row["地方公共団体名"] = cfg["name"]
        rows.append(row)

    return rows


def prepare_namegata(code, cfg, schema, header, physical_rows):
    aliases = {
        "都道府県コード又は市区町村コード": "全国地方公共団体コード",
        "NO": "ID",
        "都道府県名": "所在地_都道府県",
        "市区町村名": "所在地_市区町村",
        "住所": "所在地_連結表記",
        "男性トイレ\n総数": "男性トイレ総数",
        "男性トイレ数\n（小便器）": "男性トイレ数（小便器）",
        "男性トイレ数\n（和式）": "男性トイレ数（和式）",
        "男性トイレ数\n（洋式）": "男性トイレ数（洋式）",
        "女性トイレ\n総数": "女性トイレ総数",
        "女性トイレ数\n（和式）": "女性トイレ数（和式）",
        "女性トイレ数\n（洋式）": "女性トイレ数（洋式）",
        "男女共用トイレ\n総数": "男女共用トイレ総数",
        "男女共用トイレ数\n（和式）": "男女共用トイレ数（和式）",
        "男女共用トイレ数\n（洋式）": "男女共用トイレ数（洋式）",
        "車椅子使用者用\nトイレ有無": "車椅子使用者用トイレ有無",
        "乳幼児用設備\n設置トイレ有無": "乳幼児用設備設置トイレ有無",
        "オストメイト設置\nトイレ有無": "オストメイト設置トイレ有無",
    }

    indexes = {h: i for i, h in enumerate(header)}
    if len(indexes) != len(header):
        raise RuntimeError(f"{code}: unexpected duplicate headers")

    rows = []
    all_day_rows = 0
    time_normalized = 0

    for line_no, srcrow in enumerate(physical_rows, 2):
        clean = {
            h: (srcrow[i] if i < len(srcrow) else "").strip()
            for h, i in indexes.items()
        }
        if not any(clean.values()):
            continue

        row = {c: clean.get(c, "") for c in schema}
        for old, new in aliases.items():
            row[new] = clean.get(old, "")

        row["地方公共団体名"] = cfg["name"]

        if clean.get("多機能トイレ数"):
            RowSupport.append_note(row, f"原データ多機能トイレ数={clean['多機能トイレ数']}")

        start = clean.get("利用開始時間", "")
        end = clean.get("利用終了時間", "")
        if start == "終日" or end == "終日":
            if start != "終日" or end != "終日":
                raise RuntimeError(
                    f"{code}:{line_no}: asymmetric 終日 values: {start!r}/{end!r}"
                )
            RowSupport.append_note(row, "原データ利用開始時間=終日")
            RowSupport.append_note(row, "原データ利用終了時間=終日")
            row["利用開始時間"] = "00:00"
            row["利用終了時間"] = "23:59"
            all_day_rows += 1
        elif start == "8:30":
            row["利用開始時間"] = "08:30"
            time_normalized += 1

        rows.append(row)

    return rows


def prepare_meguro(code, cfg, schema, header, physical_rows):
    aliases = {
        "都道府県コード又は市区町村コード": "全国地方公共団体コード",
        "NO": "ID",
        "都道府県名": "所在地_都道府県",
        "市区町村名": "所在地_市区町村",
        "住所": "所在地_連結表記",
        "方書": "建物名等(方書)",
    }

    indexes = {h: i for i, h in enumerate(header)}
    if len(indexes) != len(header):
        raise RuntimeError(f"{code}: unexpected duplicate headers")

    bool_fields = (
        "車椅子使用者用トイレ有無",
        "乳幼児用設備設置トイレ有無",
        "オストメイト設置トイレ有無",
    )
    rows = []
    boolean_changes = 0

    for line_no, srcrow in enumerate(physical_rows, 2):
        clean = {
            h: (srcrow[i] if i < len(srcrow) else "").strip()
            for h, i in indexes.items()
        }
        if not any(clean.values()):
            continue

        row = {c: clean.get(c, "") for c in schema}
        for old, new in aliases.items():
            row[new] = clean.get(old, "")

        row["地方公共団体名"] = cfg["name"]

        if clean.get("多機能トイレ数"):
            RowSupport.append_note(row, f"原データ多機能トイレ数={clean['多機能トイレ数']}")

        floor = clean.get("備考（床面積㎡）", "")
        if floor:
            RowSupport.append_note(row, f"原データ備考（床面積㎡）={floor}")

        for field in bool_fields:
            v = (row.get(field) or "").strip()
            if v == "○":
                RowSupport.append_note(row, f"原データ{field}=○")
                row[field] = "有"
                boolean_changes += 1
            elif v == "×":
                RowSupport.append_note(row, f"原データ{field}=×")
                row[field] = "無"
                boolean_changes += 1
            elif v not in ("", "有", "無"):
                raise RuntimeError(
                    f"{code}:{line_no}: unexpected boolean {field}={v!r}"
                )

        rows.append(row)

    return rows


def prepare_one(code, cfg, schema):
    src = ROOT / "data/raw" / cfg["pref"] / cfg["mun"] / "public-toilet" / cfg["file"]
    dest = ROOT / "data/normalized" / cfg["pref"] / cfg["mun"] / "public-toilet/public-toilet.csv"

    if not src.exists():
        raise RuntimeError(f"{code}: raw missing: {src}")
    if dest.exists():
        raise RuntimeError(f"{code}: normalized already exists: {dest}")

    enc, header, physical_rows = read_positional(src)

    if cfg["kind"] == "noshiro":
        rows = prepare_noshiro(code, cfg, schema, header, physical_rows)
    elif cfg["kind"] == "namegata":
        rows = prepare_namegata(code, cfg, schema, header, physical_rows)
    elif cfg["kind"] == "meguro":
        rows = prepare_meguro(code, cfg, schema, header, physical_rows)
    else:
        raise RuntimeError(f"unknown kind: {cfg['kind']}")

    ids = [r["ID"] for r in rows if r["ID"]]
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"{code}: duplicate nonblank IDs after mapping")

    return dest, enc, rows



def main():
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    prepared = []
    for code, cfg in TARGETS.items():
        dest, enc, rows = prepare_one(code, cfg, schema)
        prepared.append((code, cfg, dest, enc, rows))

    print(f"preflight OK: {len(prepared)} municipalities")

    for code, cfg, dest, enc, rows in prepared:
        StandardCsvWriter().write(dest, schema, rows)
        print(f"OK {code} {cfg['name']}: rows={len(rows)} encoding={enc}")


if __name__ == "__main__":
    main()
