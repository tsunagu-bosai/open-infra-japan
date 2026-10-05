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
    "08202": {
        "pref": "08-茨城県", "mun": "08202-日立市", "name": "日立市",
        "file": "082023_publictoilet2.csv", "encoding": "utf-8-sig",
        "kind": "hitachi",
    },
    "13113": {
        "pref": "13-東京都", "mun": "13113-渋谷区", "name": "渋谷区",
        "file": "131130_public_toilet_list_9219741612665975582.csv", "encoding": "utf-8-sig",
        "kind": "shibuya",
    },
    "13114": {
        "pref": "13-東京都", "mun": "13114-中野区", "name": "中野区",
        "file": "13114_public-toilet.csv", "encoding": "utf-8-sig",
        "kind": "nakano",
    },
    "18207": {
        "pref": "18-福井県", "mun": "18207-鯖江市", "name": "鯖江市",
        "file": "18207_public-toilet.csv", "encoding": "cp932",
        "kind": "sabae",
    },
}



def append_time_note(row, text):
    text = (text or "").strip()
    if not text:
        return
    cur = (row.get("利用可能時間特記事項") or "").strip()
    row["利用可能時間特記事項"] = f"{cur} / {text}" if cur else text


def read_dicts(path, encoding):
    with path.open("r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or [], list(reader)


def sum_if_any(*values):
    vals = [(v or "").strip() for v in values]
    if not any(vals):
        return ""
    total = 0
    for v in vals:
        if not v:
            continue
        if not v.isdigit():
            raise RuntimeError(f"non-numeric component: {v!r}")
        total += int(v)
    return str(total)


def prepare_hitachi(code5, cfg, schema, src):
    with src.open("r", encoding=cfg["encoding"], newline="") as f:
        physical = list(csv.reader(f))
    header, data = physical[0], physical[1:]
    expected = ["No.", "施設名称", "施設名称", "施設所在"]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    out = []
    for line_no, r in enumerate(data, 2):
        if len(r) != 4:
            raise RuntimeError(f"{code5}:{line_no}: bad width")
        no, parent_name, toilet_name, address = [x.strip() for x in r]
        row = {k: "" for k in schema}
        row["全国地方公共団体コード"] = six_digit_municipality_code(code5)
        row["地方公共団体名"] = cfg["name"]
        row["ID"] = no
        row["名称"] = toilet_name
        row["所在地_連結表記"] = address
        row["所在地_都道府県"] = "茨城県"
        row["所在地_市区町村"] = cfg["name"]
        if parent_name and parent_name != toilet_name:
            RowSupport.append_note(row, f"原データ施設名称(上位施設)={parent_name}")
        out.append(row)

    return out, {"parent_facility_preserved": sum(1 for r in out if r["備考"])}


def prepare_shibuya(code5, cfg, schema, src):
    header, rows = read_dicts(src, cfg["encoding"])
    expected = [
        '全国地方公共団体コード', 'No', '名称', '名称_カナ', '名称_英字',
        '所在地_全国地方公共団体コード', '所在地_連結表記', '所在地_都道府県',
        '所在地_市区町村', '所在地_町字', '所在地_番地以下', '建物名等(方書)',
        '設置位置', '緯度', '経度', '男性トイレ_総数', '男性トイレ数_小便器',
        '男性トイレ数_和式', '男性トイレ数_洋式', '女性トイレ_総数',
        '女性トイレ数_和式', '女性トイレ数_洋式', '男女共用トイレ_総数',
        '男女共用トイレ数_和式', '男女共用トイレ数_洋式', '多機能トイレ数',
        '車椅子使用者用トイレの数', '車椅子使用者用トイレ有無',
        '乳幼児用設備設置トイレ有無', 'オストメイト設置トイレ有無',
        '利用開始時間', '利用終了時間', '利用可能時間特記事項', '画像URL',
        '画像_ライセンス', 'URL', '備考', 'ObjectId', 'x', 'y'
    ]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    alias = {
        "No": "ID",
        "名称": "名称",
        "名称_カナ": "名称_カナ",
        "名称_英字": "名称_英語",
        "所在地_全国地方公共団体コード": "所在地_全国地方公共団体コード",
        "所在地_連結表記": "所在地_連結表記",
        "所在地_都道府県": "所在地_都道府県",
        "所在地_市区町村": "所在地_市区町村",
        "所在地_町字": "所在地_町字",
        "所在地_番地以下": "所在地_番地以下",
        "建物名等(方書)": "建物名等(方書)",
        "設置位置": "設置位置",
        "緯度": "緯度",
        "経度": "経度",
        "男性トイレ_総数": "男性トイレ総数",
        "男性トイレ数_小便器": "男性トイレ数（小便器）",
        "男性トイレ数_和式": "男性トイレ数（和式）",
        "男性トイレ数_洋式": "男性トイレ数（洋式）",
        "女性トイレ_総数": "女性トイレ総数",
        "女性トイレ数_和式": "女性トイレ数（和式）",
        "女性トイレ数_洋式": "女性トイレ数（洋式）",
        "男女共用トイレ_総数": "男女共用トイレ総数",
        "男女共用トイレ数_和式": "男女共用トイレ数（和式）",
        "男女共用トイレ数_洋式": "男女共用トイレ数（洋式）",
        "車椅子使用者用トイレ有無": "車椅子使用者用トイレ有無",
        "乳幼児用設備設置トイレ有無": "乳幼児用設備設置トイレ有無",
        "オストメイト設置トイレ有無": "オストメイト設置トイレ有無",
        "利用開始時間": "利用開始時間",
        "利用終了時間": "利用終了時間",
        "利用可能時間特記事項": "利用可能時間特記事項",
        "画像URL": "画像",
        "画像_ライセンス": "画像_ライセンス",
        "備考": "備考",
    }

    out = []
    for line_no, s in enumerate(rows, 2):
        c = {k: (v or "").strip() for k, v in s.items()}
        if c["全国地方公共団体コード"] != "131130":
            raise RuntimeError(f"{code5}:{line_no}: bad municipality code")
        row = {k: "" for k in schema}
        row["全国地方公共団体コード"] = c["全国地方公共団体コード"]
        row["地方公共団体名"] = cfg["name"]
        for old, new in alias.items():
            row[new] = c[old]

        # Do not equate multifunctional toilet count with barrier-free count.
        RowSupport.append_note(row, f"原データ多機能トイレ数={c['多機能トイレ数']}")
        if c["車椅子使用者用トイレの数"]:
            RowSupport.append_note(row, f"原データ車椅子使用者用トイレの数={c['車椅子使用者用トイレの数']}")
        if c["URL"]:
            RowSupport.append_note(row, f"原データURL={c['URL']}")
        if c["ObjectId"]:
            RowSupport.append_note(row, f"原データObjectId={c['ObjectId']}")
        if c["x"]:
            RowSupport.append_note(row, f"原データx={c['x']}")
        if c["y"]:
            RowSupport.append_note(row, f"原データy={c['y']}")
        out.append(row)

    return out, {"multifunction_preserved": len(out)}


def prepare_nakano(code5, cfg, schema, src):
    header, rows = read_dicts(src, cfg["encoding"])
    expected = [
        '都道府県コード又は市区町村コード', '都道府県名', '市区町村名', '名称',
        '名称_カナ', '名称_英語', '住所', '設置位置', '車いす使用者用トイレ',
        '男子大便器洋式', '男子大便器和式', '男子小便器', '女子便器洋式',
        '女子便器和式', '共用便器洋式', '共用便器和式', 'トイレットペーパー',
        'ベビーシート', 'ベビーチェア', 'オストメイト', '備考', '経度', '緯度', '分類'
    ]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    out = []
    for line_no, s in enumerate(rows, 2):
        c = {k: (v or "").strip() for k, v in s.items()}
        if c["都道府県コード又は市区町村コード"] != "131148":
            raise RuntimeError(f"{code5}:{line_no}: bad municipality code")

        for f in ("ベビーシート", "ベビーチェア"):
            if c[f] not in ("", "あり", "なし"):
                raise RuntimeError(f"{code5}:{line_no}: unexpected {f}={c[f]!r}")

        row = {k: "" for k in schema}
        row["全国地方公共団体コード"] = c["都道府県コード又は市区町村コード"]
        row["地方公共団体名"] = cfg["name"]
        row["名称"] = c["名称"]
        row["名称_カナ"] = c["名称_カナ"]
        row["名称_英語"] = c["名称_英語"]
        row["所在地_連結表記"] = c["住所"]
        row["所在地_都道府県"] = c["都道府県名"]
        row["所在地_市区町村"] = c["市区町村名"]
        row["設置位置"] = c["設置位置"]
        row["緯度"] = c["緯度"]
        row["経度"] = c["経度"]

        row["男性トイレ数（小便器）"] = c["男子小便器"]
        row["男性トイレ数（和式）"] = c["男子大便器和式"]
        row["男性トイレ数（洋式）"] = c["男子大便器洋式"]
        row["女性トイレ数（和式）"] = c["女子便器和式"]
        row["女性トイレ数（洋式）"] = c["女子便器洋式"]
        row["男女共用トイレ数（和式）"] = c["共用便器和式"]
        row["男女共用トイレ数（洋式）"] = c["共用便器洋式"]

        row["男性トイレ総数"] = sum_if_any(
            c["男子小便器"], c["男子大便器和式"], c["男子大便器洋式"]
        )
        row["女性トイレ総数"] = sum_if_any(c["女子便器和式"], c["女子便器洋式"])
        row["男女共用トイレ総数"] = sum_if_any(c["共用便器和式"], c["共用便器洋式"])

        if c["車いす使用者用トイレ"]:
            if not c["車いす使用者用トイレ"].isdigit():
                raise RuntimeError(f"{code5}:{line_no}: bad wheelchair value")
            row["車椅子使用者用トイレ有無"] = (
                "有" if int(c["車いす使用者用トイレ"]) > 0 else "無"
            )

        baby = {c["ベビーシート"], c["ベビーチェア"]} - {""}
        if "あり" in baby:
            row["乳幼児用設備設置トイレ有無"] = "有"
        elif baby == {"なし"}:
            row["乳幼児用設備設置トイレ有無"] = "無"

        if c["オストメイト"]:
            row["オストメイト設置トイレ有無"] = "無" if c["オストメイト"] == "なし" else "有"

        row["備考"] = c["備考"]
        RowSupport.append_note(row, f"原データトイレットペーパー={c['トイレットペーパー']}")
        RowSupport.append_note(row, f"原データベビーシート={c['ベビーシート']}")
        RowSupport.append_note(row, f"原データベビーチェア={c['ベビーチェア']}")
        RowSupport.append_note(row, f"原データオストメイト={c['オストメイト']}")
        RowSupport.append_note(row, f"原データ分類={c['分類']}")

        if any(k in c["備考"] for k in ("開放", "閉鎖", "時間")):
            append_time_note(row, c["備考"])

        out.append(row)

    return out, {"blank_ids": len(out), "derived_totals": len(out)}


def normalize_sabae_time(value, row, field):
    v = (value or "").strip()
    if not v:
        return ""
    parts = v.split(":")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise RuntimeError(f"unexpected time {field}={v!r}")
    h, m, s = map(int, parts)
    if s != 0:
        raise RuntimeError(f"nonzero seconds {field}={v!r}")
    if h == 24 and m == 0:
        RowSupport.append_note(row, f"原データ{field}={v}")
        return "23:59"
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise RuntimeError(f"invalid time {field}={v!r}")
    return f"{h:02d}:{m:02d}"


def prepare_sabae(code5, cfg, schema, src):
    with src.open("r", encoding=cfg["encoding"], newline="") as f:
        physical = list(csv.reader(f))
    header, data = physical[0], physical[1:]
    expected = [
        '施設名', '施設名(英語)', '都道府県名', '市区町村名', '行政区名', '住所',
        '住所(かな)', '電話番号', '緯度', '経度', '利用可能時間OPENS',
        '利用可能時間CLOSES', '説明(日本語)', '説明(英語)', '調査年月日',
        '男性トイレ数', '女性トイレ数', '男女共用トイレ数', 'バリアフリートイレ数',
        'オストメイト', '多目的シート（ユニバーサルシート）', 'ベビーチェア',
        'ベビーベット', '固定手すり', '可動手すり', '幼児用便器', '自動扉',
        '出入口の表示', '非常用呼出ボタン', '車椅子対応エレベーター',
        '車椅子対応エスカレーター', '授乳スペース', 'おむつ交換台', 'AED',
        '画像URL', '画像URL', '画像URL', '画像URL', '標準地域コード'
    ]
    if header != expected:
        raise RuntimeError(f"{code5}: header drift")

    out = []
    corrected_24 = 0
    for line_no, r in enumerate(data, 2):
        if len(r) != len(header):
            raise RuntimeError(f"{code5}:{line_no}: bad width")
        c = {f"c{i}": (v or "").strip() for i, v in enumerate(r)}

        row = {k: "" for k in schema}
        row["全国地方公共団体コード"] = six_digit_municipality_code(code5)
        row["地方公共団体名"] = cfg["name"]
        row["名称"] = c["c0"]
        row["名称_英語"] = c["c1"]
        row["所在地_都道府県"] = c["c2"] or "福井県"
        row["所在地_市区町村"] = c["c3"] or cfg["name"]
        row["所在地_連結表記"] = c["c5"]
        row["緯度"] = c["c8"]
        row["経度"] = c["c9"]

        row["男性トイレ総数"] = c["c15"]
        row["女性トイレ総数"] = c["c16"]
        row["男女共用トイレ総数"] = c["c17"]
        row["バリアフリートイレ数"] = c["c18"]

        if c["c19"]:
            if not c["c19"].isdigit():
                raise RuntimeError(f"{code5}:{line_no}: bad ostomate value")
            row["オストメイト設置トイレ有無"] = "有" if int(c["c19"]) > 0 else "無"

        before = len(row["備考"])
        row["利用開始時間"] = normalize_sabae_time(c["c10"], row, "利用可能時間OPENS")
        row["利用終了時間"] = normalize_sabae_time(c["c11"], row, "利用可能時間CLOSES")
        if "24:00:00" in row["備考"]:
            corrected_24 += 1

        if c["c12"]:
            RowSupport.append_note(row, f"原データ説明(日本語)={c['c12']}")
        if c["c13"]:
            RowSupport.append_note(row, f"原データ説明(英語)={c['c13']}")
        if c["c14"]:
            RowSupport.append_note(row, f"原データ調査年月日={c['c14']}")

        extras = [
            ("多目的シート（ユニバーサルシート）", c["c20"]),
            ("ベビーチェア", c["c21"]),
            ("ベビーベット", c["c22"]),
            ("固定手すり", c["c23"]),
            ("可動手すり", c["c24"]),
            ("幼児用便器", c["c25"]),
            ("自動扉", c["c26"]),
            ("出入口の表示", c["c27"]),
            ("非常用呼出ボタン", c["c28"]),
            ("車椅子対応エレベーター", c["c29"]),
            ("車椅子対応エスカレーター", c["c30"]),
            ("授乳スペース", c["c31"]),
            ("おむつ交換台", c["c32"]),
            ("AED", c["c33"]),
            ("標準地域コード", c["c38"]),
        ]
        for k, v in extras:
            if v:
                RowSupport.append_note(row, f"原データ{k}={v}")

        images = [c["c34"], c["c35"], c["c36"], c["c37"]]
        nonblank_images = [v for v in images if v]
        if nonblank_images:
            row["画像"] = nonblank_images[0]
            for i, v in enumerate(nonblank_images[1:], 2):
                RowSupport.append_note(row, f"原データ画像URL{i}={v}")

        out.append(row)

    return out, {"blank_ids": len(out), "end_24_corrected": corrected_24}


PREP = {
    "hitachi": prepare_hitachi,
    "shibuya": prepare_shibuya,
    "nakano": prepare_nakano,
    "sabae": prepare_sabae,
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
            raise RuntimeError(f"{code5}: source missing {src}")
        if dest.exists():
            raise RuntimeError(f"{code5}: normalized already exists {dest}")

        rows, stats = PREP[cfg["kind"]](code5, cfg, schema, src)
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
