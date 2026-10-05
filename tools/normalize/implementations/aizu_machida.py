#!/usr/bin/env python3
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.normalization import RowSupport, StandardCsvWriter

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "07202": {
        "pref": "07-福島県",
        "mun": "07202-会津若松市",
        "file": "07202_public-toilet.csv",
        "name": "会津若松市",
        "kind": "aizu",
    },
    "13209": {
        "pref": "13-東京都",
        "mun": "13209-町田市",
        "file": "13209_public-toilet.csv",
        "name": "町田市",
        "kind": "machida",
    },
}



def hhmm(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    parts = value.replace("：", ":").split(":")
    if len(parts) == 2 and all(p.isdigit() for p in parts):
        h, m = map(int, parts)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return f"{h:02d}:{m:02d}"
    raise RuntimeError(f"not hh:mm: {value!r}")


def read_dicts(path: Path, enc: str):
    with path.open("r", encoding=enc, newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or [], list(reader)


def prepare_aizu(code, cfg, schema, src):
    header, rows = read_dicts(src, "utf-8-sig")

    expected = [
        'localgov_code', 'id', 'localgov_name', 'name', 'name_kana',
        'name_english', 'seat_localgov_code', 'choaza_id',
        'seat_copulative_spell', 'seat_prefecture', 'seat_city',
        'seat_choaza', 'seat_after_address', 'buillding_name_etc',
        'set_position', 'latitude', 'longitude',
        'advanced_classification', 'advanced_value',
        'male_wc_total', 'male_wc_urinal', 'male_wc_jstyle',
        'male_wc_wstyle', 'female_wc_total', 'female_wc_jstyle',
        'female_wc_wstyle', 'unisex_wc_total', 'unisex_wc_jstyle',
        'unisex_wc_wstyle', 'barrier_free_wc', 'wheelchair_wc',
        'infant_wc', 'ostomate_wc', 'available_start_time',
        'available_end_time', 'available_time_note', 'image',
        'image_licence', 'note'
    ]
    if header != expected:
        raise RuntimeError(f"{code}: source header drift")

    mapping = {
        "localgov_code": "全国地方公共団体コード",
        "id": "ID",
        "localgov_name": "地方公共団体名",
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

    out = []
    infant_preserved = 0
    time_notes = 0

    for line_no, srcrow in enumerate(rows, 2):
        clean = {k: (v or "").strip() for k, v in srcrow.items()}

        if clean["localgov_code"] != "072028":
            raise RuntimeError(f"{code}:{line_no}: bad localgov_code")
        if clean["seat_localgov_code"] != "072028":
            raise RuntimeError(f"{code}:{line_no}: bad seat_localgov_code")

        row = {c: "" for c in schema}
        for old, new in mapping.items():
            row[new] = clean[old]

        # Source custom fields do not have standard boolean semantics here.
        if clean["wheelchair_wc"]:
            RowSupport.append_note(row, f"原データwheelchair_wc={clean['wheelchair_wc']}")
        if clean["infant_wc"]:
            RowSupport.append_note(row, f"原データinfant_wc={clean['infant_wc']}")
            infant_preserved += 1
        if clean["ostomate_wc"]:
            RowSupport.append_note(row, f"原データostomate_wc={clean['ostomate_wc']}")

        if clean["available_start_time"]:
            RowSupport.append_note(row, f"原データavailable_start_time={clean['available_start_time']}")
        if clean["available_end_time"]:
            RowSupport.append_note(row, f"原データavailable_end_time={clean['available_end_time']}")

        if clean["available_time_note"]:
            row["利用可能時間特記事項"] = clean["available_time_note"]
            time_notes += 1

        out.append(row)

    return out, {
        "infant_values_preserved": infant_preserved,
        "time_notes_preserved": time_notes,
    }


def prepare_machida(code, cfg, schema, src):
    header, rows = read_dicts(src, "cp932")

    expected = [
        "都道府県コード又は市区町村コード", "No", "都道府県名",
        "市区町村名", "名称", "住所", "緯度", "経度",
        "車椅子使用者トイレ有無", "乳幼児用設備設置トイレ有無",
        "オストメイトトイレ設置トイレ有無", "利用開始時間",
        "利用終了時間", "利用可能時間特記事項", "施設種類",
        "No_0", "マッチレベル", "移動年月日",
    ]
    if header != expected:
        raise RuntimeError(f"{code}: source header drift")

    id_counts = Counter((r.get("No") or "").strip() for r in rows)
    duplicate_ids = {v for v, n in id_counts.items() if v and n > 1}

    out = []
    id_cleared = 0
    raw_code_corrected = 0

    for line_no, srcrow in enumerate(rows, 2):
        c = {k: (v or "").strip() for k, v in srcrow.items()}

        if c["都道府県コード又は市区町村コード"] != "132,098":
            raise RuntimeError(f"{code}:{line_no}: unexpected source code")

        row = {x: "" for x in schema}
        row["全国地方公共団体コード"] = "132098"
        row["地方公共団体名"] = cfg["name"]

        raw_id = c["No"]
        if not raw_id or raw_id in duplicate_ids:
            if raw_id:
                RowSupport.append_note(row, f"原データID={raw_id}")
            row["ID"] = ""
            id_cleared += 1
        else:
            row["ID"] = raw_id

        row["所在地_都道府県"] = c["都道府県名"]
        row["所在地_市区町村"] = c["市区町村名"]
        row["名称"] = c["名称"]
        row["所在地_連結表記"] = c["住所"]
        row["緯度"] = c["緯度"]
        row["経度"] = c["経度"]

        row["車椅子使用者用トイレ有無"] = c["車椅子使用者トイレ有無"]
        row["乳幼児用設備設置トイレ有無"] = c["乳幼児用設備設置トイレ有無"]
        row["オストメイト設置トイレ有無"] = c["オストメイトトイレ設置トイレ有無"]

        row["利用開始時間"] = hhmm(c["利用開始時間"]) if c["利用開始時間"] else ""
        row["利用終了時間"] = hhmm(c["利用終了時間"]) if c["利用終了時間"] else ""
        row["利用可能時間特記事項"] = c["利用可能時間特記事項"]

        RowSupport.append_note(row, "原データ全国地方公共団体コード=132,098")
        RowSupport.append_note(row, f"原データ施設種類={c['施設種類']}")
        if c["マッチレベル"]:
            RowSupport.append_note(row, f"原データマッチレベル={c['マッチレベル']}")
        if c["移動年月日"]:
            RowSupport.append_note(row, f"原データ移動年月日={c['移動年月日']}")

        raw_code_corrected += 1
        out.append(row)

    ids = [r["ID"] for r in out if r["ID"]]
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"{code}: duplicate IDs remain")

    return out, {
        "code_corrected": raw_code_corrected,
        "id_cleared": id_cleared,
    }



def main():
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    prepared = []

    for code, cfg in TARGETS.items():
        src = ROOT / "data/raw" / cfg["pref"] / cfg["mun"] / "public-toilet" / cfg["file"]
        dest = ROOT / "data/normalized" / cfg["pref"] / cfg["mun"] / "public-toilet/public-toilet.csv"

        if not src.exists():
            raise RuntimeError(f"{code}: source missing: {src}")
        if dest.exists():
            raise RuntimeError(f"{code}: normalized already exists: {dest}")

        if cfg["kind"] == "aizu":
            rows, stats = prepare_aizu(code, cfg, schema, src)
            enc = "utf-8-sig"
        else:
            rows, stats = prepare_machida(code, cfg, schema, src)
            enc = "cp932"

        prepared.append((code, cfg, dest, enc, rows, stats))

    print(f"preflight OK: {len(prepared)} municipalities")

    for code, cfg, dest, enc, rows, stats in prepared:
        StandardCsvWriter().write(dest, schema, rows)
        detail = " ".join(f"{k}={v}" for k, v in stats.items())
        print(
            f"OK {code} {cfg['name']}: rows={len(rows)} "
            f"encoding={enc} {detail}"
        )


if __name__ == "__main__":
    main()
