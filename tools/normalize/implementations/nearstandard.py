#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from tools.normalize.core.schema import read_schema_fields
from tools import normalize_public_toilet as common
from tools.normalize.core.normalization import (
    CsvDictSourceReader,
    XlsxSourceReader,
    RowSupport,
    Sha256StableIdStrategy,
    StandardCsvWriter,
)

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "14211": {
        "pref": "14-神奈川県",
        "mun": "14211-秦野市",
        "file": "public_toilet.csv",
        "aliases": {
            "全国地方公共団体ｺｰﾄﾞ": "全国地方公共団体コード",
            "名称_ｶﾅ": "名称_カナ",
            "所在地_全国地方公共団体ｺｰﾄﾞ": "所在地_全国地方公共団体コード",
            "男性ﾄｲﾚ総数": "男性トイレ総数",
            "男性ﾄｲﾚ数(小便器)": "男性トイレ数（小便器）",
            "男性ﾄｲﾚ数(和式)": "男性トイレ数（和式）",
            "男性ﾄｲﾚ数(洋式)": "男性トイレ数（洋式）",
            "女性ﾄｲﾚ総数": "女性トイレ総数",
            "女性ﾄｲﾚ数(和式)": "女性トイレ数（和式）",
            "女性ﾄｲﾚ数(洋式)": "女性トイレ数（洋式）",
            "男女共用ﾄｲﾚ総数": "男女共用トイレ総数",
            "男女共用ﾄｲﾚ数(和式)": "男女共用トイレ数（和式）",
            "男女共用ﾄｲﾚ数(洋式)": "男女共用トイレ数（洋式）",
            "ﾊﾞﾘｱﾌﾘｰﾄｲﾚ数": "バリアフリートイレ数",
            "車椅子使用者用ﾄｲﾚ有無": "車椅子使用者用トイレ有無",
            "乳幼児用設備設置ﾄｲﾚ有無": "乳幼児用設備設置トイレ有無",
            "ｵｽﾄﾒｲﾄ設置ﾄｲﾚ有無": "オストメイト設置トイレ有無",
        },
        "preserve": [],
        "allowed_missing": {
            "町字ID",
            "高度の種別",
            "高度の値",
        },
    },
    "19209": {
        "pref": "19-山梨県",
        "mun": "19209-北杜市",
        "file": "192091_public_toilet.csv",
        "aliases": {},
        "preserve": [],
        "allowed_missing": {
            "所在地_全国地方公共団体コード",
            "所在地_連結表記",
        },
    },
    "23211": {
        "pref": "23-愛知県",
        "mun": "23211-豊田市",
        "file": "23211_public-toilet.csv",
        "aliases": {},
        "preserve": [],
        "allowed_missing": {
            "ID",
            "高度の種別",
            "高度の値",
        },
    },
    "29425": {
        "pref": "29-奈良県",
        "mun": "29425-王寺町",
        "file": "294250_public_toilet_csv_2025.csv",
        "aliases": {
            "1.名称": "名称",
            "2.名称_カナ": "名称_カナ",
            "3.名称_英語": "名称_英語",
            "4.所在地_連結表記": "所在地_連結表記",
            "5.所在地_都道府県": "所在地_都道府県",
            "6.所在地_市区町村": "所在地_市区町村",
            "7.所在地_町字": "所在地_町字",
            "8.所在地_番地以下": "所在地_番地以下",
            "9.建物名等(方書)": "建物名等(方書)",
            "10.設置位置": "設置位置",
            "11.緯度": "緯度",
            "12.経度": "経度",
            "13.男性トイレ総数": "男性トイレ総数",
            "14.男性トイレ数（小便器）": "男性トイレ数（小便器）",
            "15.男性トイレ数（和式）": "男性トイレ数（和式）",
            "16.男性トイレ数（洋式）": "男性トイレ数（洋式）",
            "17.女性トイレ総数": "女性トイレ総数",
            "18.女性トイレ数（和式）": "女性トイレ数（和式）",
            "19.女性トイレ数（洋式）": "女性トイレ数（洋式）",
            "20.男女共用トイレ総数": "男女共用トイレ総数",
            "21.男女共用トイレ数（和式）": "男女共用トイレ数（和式）",
            "22.男女共用トイレ数（洋式）": "男女共用トイレ数（洋式）",
            "23.バリアフリートイレ数": "バリアフリートイレ数",
            "24.車椅子使用者用トイレ有無": "車椅子使用者用トイレ有無",
            "25.乳幼児用設備設置トイレ有無": "乳幼児用設備設置トイレ有無",
            "26.オストメイト設置トイレ有無": "オストメイト設置トイレ有無",
            "27.利用開始時間": "利用開始時間",
            "28.利用終了時間": "利用終了時間",
            "29.利用可能時間特記事項": "利用可能時間特記事項",
        },
        "preserve": [],
        "allowed_missing": set(),
    },
    "29206": {
        "pref": "29-奈良県",
        "mun": "29206-桜井市",
        "file": "292061_public_toilet.csv",
        "aliases": {},
        "preserve": [],
        "allowed_missing": set(),
    },
    "29363": {
        "pref": "29-奈良県",
        "mun": "29363-田原本町",
        "file": "293636_public_toilet.csv",
        "aliases": {},
        "preserve": [],
        "allowed_missing": set(),
    },
    "28501": {
        "pref": "28-兵庫県",
        "mun": "28501-佐用町",
        "file": "285013_public_toilet_list.csv",
        "reader": "csv",
        "aliases": {
            "id": "ID",
            "建物名等_方書": "建物名等(方書)",
            "男性トイレ数_小便器": "男性トイレ数（小便器）",
            "男性トイレ数_和式": "男性トイレ数（和式）",
            "男性トイレ数_洋式": "男性トイレ数（洋式）",
            "女性トイレ数_和式": "女性トイレ数（和式）",
            "女性トイレ数_洋式": "女性トイレ数（洋式）",
            "男女共用トイレ数_和式": "男女共用トイレ数（和式）",
            "男女共用トイレ数_洋式": "男女共用トイレ数（洋式）",
        },
        "preserve": ["No"],
        "ignore": ["都道府県名", ""],
        "allowed_missing": set(),
    },
    "28586": {
        "pref": "28-兵庫県",
        "mun": "28586-新温泉町",
        "file": "28586_public-toilet.xlsx",
        "reader": "xlsx",
        "sheet_name": "shinonsen_public_toilet",
        "aliases": {},
        "preserve": ["多機能トイレ数"],
        "ignore": [],
        "allowed_missing": set(),
    },
    "27361": {
        "pref": "27-大阪府",
        "mun": "27361-熊取町",
        "file": "27361_public-toilet.csv",
        "aliases": {
            "所在地_連結標記": "所在地_連結表記",
            "建物名（方書）": "建物名等(方書)",
        },
        "preserve": ["最終更新履歴"],
        "allowed_missing": {
            "所在地_全国地方公共団体コード",
            "町字ID",
            "高度の種別",
            "高度の値",
        },
    },
    "43215": {
        "pref": "43-熊本県",
        "mun": "43215-天草市",
        "file": "43215_public-toilet.csv",
        "aliases": {
            "所在地_連結標記": "所在地_連結表記",
            "建物名等（方書）": "建物名等(方書)",
            "画像ライセンス": "画像_ライセンス",
        },
        "preserve": [],
        "allowed_missing": {
            "設置位置",
        },
    },
    "43433": {
        "pref": "43-熊本県",
        "mun": "43433-南阿蘇村",
        "file": "43433_public-toilet.csv",
        "aliases": {
            "所在地_連結標記": "所在地_連結表記",
            "建物名等（方書）": "建物名等(方書)",
            "画像ライセンス": "画像_ライセンス",
        },
        "preserve": [],
        "allowed_missing": {
            "設置位置",
        },
    },
}



STABLE_ID = Sha256StableIdStrategy()
READER = CsvDictSourceReader()
WRITER = StandardCsvWriter()


def prepare_one(code, cfg, schema):
    src = ROOT / "data/raw" / cfg["pref"] / cfg["mun"] / "public-toilet" / cfg["file"]
    dest = ROOT / "data/normalized" / cfg["pref"] / cfg["mun"] / "public-toilet/public-toilet.csv"

    if not src.exists():
        raise RuntimeError(f"{code}: raw missing: {src}")
    if dest.exists():
        raise RuntimeError(f"{code}: normalized already exists: {dest}")

    reader_kind = cfg.get("reader", "csv")
    if reader_kind == "csv":
        reader = READER
    elif reader_kind == "xlsx":
        reader = XlsxSourceReader(cfg["sheet_name"])
    else:
        raise RuntimeError(
            f"{code}: unknown reader={reader_kind!r}"
        )

    source = reader.read(src)
    enc = source.source_format
    header = source.header
    if len(set(header)) != len(header):
        raise RuntimeError(f"{code}: duplicate header names found")

    aliases = cfg["aliases"]
    preserve = cfg["preserve"]
    ignore = cfg.get("ignore", [])
    actual_extras = {h for h in header if h not in schema}
    expected_extras = set(aliases) | set(preserve) | set(ignore)
    if actual_extras != expected_extras:
        raise RuntimeError(
            f"{code}: unexpected extra headers: "
            f"actual={sorted(actual_extras)!r} expected={sorted(expected_extras)!r}"
        )

    raw_missing = {c for c in schema if c not in header}
    mapped_targets = set(aliases.values())
    unresolved_missing = raw_missing - mapped_targets
    if unresolved_missing != cfg["allowed_missing"]:
        raise RuntimeError(
            f"{code}: unexpected unresolved missing columns: "
            f"actual={sorted(unresolved_missing)!r} "
            f"expected={sorted(cfg['allowed_missing'])!r}"
        )

    rows = []
    for line_no, clean in enumerate(source.rows, 2):
        row = {c: clean.get(c, "") for c in schema}
        for old, new in aliases.items():
            if old not in header:
                raise RuntimeError(f"{code}: alias source missing: {old!r}")
            row[new] = clean.get(old, "")
        for field in preserve:
            value = clean.get(field, "")
            if value:
                RowSupport.append_note(row, f"原データ{field}={value}")

        if code == "14211":
            if row["地方公共団体名"] != "神奈川県秦野市":
                raise RuntimeError(
                    "秦野市 unexpected 地方公共団体名="
                    f"{row['地方公共団体名']!r}"
                )
            row["地方公共団体名"] = "秦野市"
            if not row["ID"]:
                row["ID"] = STABLE_ID.generate(
                    code, row["名称"], row["所在地_連結表記"],
                    row["設置位置"], row["緯度"], row["経度"]
                )
        rows.append(row)

    if not rows:
        raise RuntimeError(f"{code}: no data rows after blank-row filtering")

    if code == "19209":
        bool_changes = 0
        time_changes = 0

        for row in rows:
            if (
                row.get("オストメイト設置トイレ有無") or ""
            ).strip() == "0":
                RowSupport.append_note(
                    row,
                    "原データオストメイト設置トイレ有無=0",
                )
                row["オストメイト設置トイレ有無"] = "無"
                bool_changes += 1

            start = (row.get("利用開始時間") or "").strip()
            end = (row.get("利用終了時間") or "").strip()

            if start != "終日" or end != "終日":
                raise RuntimeError(
                    "北杜市 unexpected times: "
                    f"start={start!r} end={end!r}"
                )

            RowSupport.append_note(row, "原データ利用開始時間=終日")
            RowSupport.append_note(row, "原データ利用終了時間=終日")
            row["利用開始時間"] = "00:00"
            row["利用終了時間"] = "23:59"
            time_changes += 2

        if bool_changes != 2:
            raise RuntimeError(
                f"北杜市 bool_changes={bool_changes} expected=2"
            )
        if time_changes != 22:
            raise RuntimeError(
                f"北杜市 time_changes={time_changes} expected=22"
            )

    if code == "23211":
        changed = 0

        for row in rows:
            start = (row.get("利用開始時間") or "").strip()

            if start == "0:00":
                row["利用開始時間"] = "00:00"
                changed += 1
            elif start not in ("", "00:00"):
                raise RuntimeError(
                    f"豊田市 unexpected 利用開始時間={start!r}"
                )

        if changed != 19:
            raise RuntimeError(
                f"豊田市 changed={changed} expected=19"
            )

    if code == "43433":
        changed = 0

        for row in rows:
            start = (row.get("利用開始時間") or "").strip()
            end = (row.get("利用終了時間") or "").strip()

            if start != "00:00" or end != "24:00":
                raise RuntimeError(
                    "南阿蘇村 unexpected times: "
                    f"start={start!r} end={end!r}"
                )

            RowSupport.append_note(row, "原データ利用終了時間=24:00")
            row["利用終了時間"] = "23:59"
            changed += 1

        if changed != 10:
            raise RuntimeError(
                f"南阿蘇村 changed={changed} expected=10"
            )

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
        source_path = (
            ROOT / "data/raw" / cfg["pref"] / cfg["mun"]
            / "public-toilet" / cfg["file"]
        )
        patches = common.load_patches(cfg["pref"], cfg["mun"])
        applied, problems = common.apply_patches(rows, patches, source_path)
        if problems:
            raise RuntimeError("\n".join(problems))

        WRITER.write(dest, schema, rows)
        print(
            f"OK {code} {cfg['mun'].split('-', 1)[1]}: "
            f"rows={len(rows)} encoding={enc} patches={applied}"
        )


if __name__ == "__main__":
    main()
