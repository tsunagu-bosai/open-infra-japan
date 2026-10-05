#!/usr/bin/env python3

import csv
import re
import sys
from pathlib import Path
from tools.normalize.core.normalization import (
    PreserveInvalidTimeStrategy,
    RowSupport,
    StandardCsvWriter,
)
from tools.normalize.core.schema import read_schema_fields

ROOT = Path(__file__).resolve().parents[3]

SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"
STANDARD = read_schema_fields(SCHEMA_PATH)
WRITER = StandardCsvWriter()

FILES = {
    "35202-宇部市": "35202_ube_public_toilet.csv",
    "35206-防府市": "opendata_126.csv",
    "35207-下松市": "35207_kudamatsu_public_toilet.csv",
    "35212-柳井市": "35212_yanai_public_toilet.csv",
    "35213-美祢市": "35213_mine_public_toilet.csv",
    "35215-周南市": "35215_shunan_public_toilet.csv",
    "35305-周防大島町": "35305_suo_oshima_public_toilet.csv",
    "35343-田布施町": "35343_tabuse_public_toilet.csv",
}

TARGETS = set(FILES)

HOFU33 = {
    "No": "ID",
    "名称": "名称",
    "名称_カナ": "名称_カナ",
    "名称_英語": "名称_英語",
    "住所": "所在地_連結表記",
    "方書": "建物名等(方書)",
    "設置位置": "設置位置",
    "緯度": "緯度",
    "経度": "経度",
    "男性トイレ総数": "男性トイレ総数",
    "男性トイレ数_小便器": "男性トイレ数（小便器）",
    "男性トイレ数_和式": "男性トイレ数（和式）",
    "男性トイレ数_洋式": "男性トイレ数（洋式）",
    "女性トイレ総数": "女性トイレ総数",
    "女性トイレ数_和式": "女性トイレ数（和式）",
    "女性トイレ数_洋式": "女性トイレ数（洋式）",
    "男女共用トイレ総数": "男女共用トイレ総数",
    "男女共用トイレ数_和式": "男女共用トイレ数（和式）",
    "男女共用トイレ数_洋式": "男女共用トイレ数（洋式）",
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


OLD32 = {
    "NO": "ID",
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

SHUNAN_EXTRAS = [
    "男性トイレ内の乳幼児用座椅子数",
    "男性トイレ内の乳幼児用簡易ベッド数",
    "女性トイレ内の乳幼児用座椅子数",
    "女性トイレ内の乳幼児用簡易ベッド数",
    "男女共用トイレ内の乳幼児用座椅子数",
    "男女共用トイレ内の乳幼児用簡易ベッド数",
    "バリアフリー（多目的）トイレ内の乳幼児用座椅子数",
    "バリアフリー（多目的）トイレ内の乳幼児用簡易ベッド数",
    "バリアフリー（多目的）トイレ内の簡易ベッド数（乳幼児大人兼用）",
    "バリアフリー（多目的）トイレ内の簡易着替え台数",
    "車椅子使用者用トイレ数",
    "オストメイト設置トイレ数",
]



def add_note(out, key, value):
    value = RowSupport.clean(value)
    if value == "":
        return

    part = f"{key}:{value}"
    old = RowSupport.clean(out.get("備考"))

    if old:
        if part not in old:
            out["備考"] = old + " / " + part
    else:
        out["備考"] = part


def read_csv(path, municipality):
    raw = path.read_bytes()

    text = None
    encoding = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            text = raw.decode(enc)
            encoding = enc
            break
        except UnicodeDecodeError:
            pass

    if text is None:
        raise RuntimeError(f"encoding unknown: {path}")

    rows = list(csv.reader(text.splitlines()))
    if not rows:
        return [], encoding

    header = [RowSupport.clean(x) for x in rows[0]]

    # 下松市は先頭列の見出しが誤記され、
    # 7列目と同じ「所在地_全国地方公共団体コード」になっている。
    if (
        municipality == "35207-下松市"
        and len(header) >= 7
        and header[0] == "所在地_全国地方公共団体コード"
        and header[6] == "所在地_全国地方公共団体コード"
    ):
        header[0] = "全国地方公共団体コード"

    result = []

    for row in rows[1:]:
        if not any(RowSupport.clean(v) for v in row):
            continue

        if len(row) < len(header):
            row = row + [""] * (len(header) - len(row))

        result.append(
            {
                header[i]: RowSupport.clean(row[i])
                for i in range(min(len(header), len(row)))
            }
        )

    return result, encoding


TIME_NORMALIZER = PreserveInvalidTimeStrategy()


def normalize_coordinates(out):
    lat_raw = RowSupport.clean(out["緯度"])
    lon_raw = RowSupport.clean(out["経度"])

    if not lat_raw and not lon_raw:
        return

    try:
        lat = float(lat_raw)
        lon = float(lon_raw)
    except ValueError:
        if lat_raw:
            add_note(out, "緯度_原値", lat_raw)
            out["緯度"] = ""
        if lon_raw:
            add_note(out, "経度_原値", lon_raw)
            out["経度"] = ""
        return

    # 明確な緯度経度逆転のみ修正。
    if 120 <= lat <= 150 and 20 <= lon <= 50:
        out["緯度"] = lon_raw
        out["経度"] = lat_raw


def normalize_yes_no(out):
    for field in (
        "車椅子使用者用トイレ有無",
        "乳幼児用設備設置トイレ有無",
        "オストメイト設置トイレ有無",
    ):
        value = RowSupport.clean(out[field])
        if value and value not in {"有", "無"}:
            add_note(out, f"{field}_原値", value)
            out[field] = ""


def finish(out):
    start, start_bad = TIME_NORMALIZER(out["利用開始時間"])
    end, end_bad = TIME_NORMALIZER(out["利用終了時間"])

    out["利用開始時間"] = start
    out["利用終了時間"] = end

    if start_bad:
        if start_bad in {"24時間", "終日"}:
            old = RowSupport.clean(out["利用可能時間特記事項"])
            out["利用可能時間特記事項"] = (
                f"{old} / {start_bad}" if old else start_bad
            )
        else:
            add_note(out, "利用開始時間_原値", start_bad)

    if end_bad:
        if end_bad in {"24時間", "終日"}:
            old = RowSupport.clean(out["利用可能時間特記事項"])
            out["利用可能時間特記事項"] = (
                f"{old} / {end_bad}" if old else end_bad
            )
        else:
            add_note(out, "利用終了時間_原値", end_bad)

    normalize_coordinates(out)
    normalize_yes_no(out)

    return out


def normalize_ube(row):
    out = {k: "" for k in STANDARD}

    out["ID"] = RowSupport.clean(row.get("番号"))
    out["名称"] = RowSupport.clean(row.get("公園名"))
    out["緯度"] = RowSupport.clean(row.get("緯度"))
    out["経度"] = RowSupport.clean(row.get("経度"))

    return finish(out)


def normalize_current(row, municipality):
    out = {k: "" for k in STANDARD}

    for key in STANDARD:
        if key in row:
            out[key] = RowSupport.clean(row.get(key))

    # 下松市のみ列名が旧表記。
    if municipality == "35207-下松市":
        out["利用開始時間"] = RowSupport.clean(row.get("開始時間"))
        out["利用終了時間"] = RowSupport.clean(row.get("終了時間"))

        # 数値欄に注記文字列が入っている原典データは、
        # 推測変換せず空欄にして原文を備考へ保存する。
        for field in (
            "女性トイレ数（和式）",
            "男女共用トイレ数（和式）",
        ):
            value = RowSupport.clean(out[field])
            if value:
                try:
                    float(value)
                except ValueError:
                    add_note(out, f"{field}_原値", value)
                    out[field] = ""

    return finish(out)


def normalize_hofu(row):
    out = {k: "" for k in STANDARD}

    for source, target in HOFU33.items():
        out[target] = RowSupport.clean(row.get(source))

    code = RowSupport.clean(row.get("市区町村コード"))
    if code == "352063":
        out["全国地方公共団体コード"] = code
    elif code:
        add_note(out, "市区町村コード_原値", code)

    pref = RowSupport.clean(row.get("都道府県名"))
    city = RowSupport.clean(row.get("市区町村名"))

    if pref and city:
        out["地方公共団体名"] = pref + city
    elif city:
        out["地方公共団体名"] = city
    elif pref:
        out["地方公共団体名"] = pref

    out["所在地_都道府県"] = pref
    out["所在地_市区町村"] = city

    # 「多機能トイレ数」を標準のバリアフリートイレ数と断定しない。
    multi = RowSupport.clean(row.get("多機能トイレ数"))
    if multi:
        add_note(out, "多機能トイレ数", multi)

    # 「分類」は全行でデータセット名と同じ「公衆トイレ一覧」のため、
    # 施設属性として39列へ転記しない。原本にはそのまま保持される。

    return finish(out)


def normalize_old32(row):
    out = {k: "" for k in STANDARD}

    for source, target in OLD32.items():
        out[target] = RowSupport.clean(row.get(source))

    code = RowSupport.clean(
        row.get("市区町村コード")
        or row.get("都道府県コード又は市区町村コード")
    )

    if re.fullmatch(r"\d{6}", code):
        out["全国地方公共団体コード"] = code
    elif code:
        add_note(out, "都道府県コード又は市区町村コード", code)

    pref = RowSupport.clean(row.get("都道府県名"))
    city = RowSupport.clean(row.get("市区町村名"))

    if pref and city:
        out["地方公共団体名"] = pref + city
    elif city:
        out["地方公共団体名"] = city
    elif pref:
        out["地方公共団体名"] = pref

    out["所在地_都道府県"] = pref
    out["所在地_市区町村"] = city

    multi = RowSupport.clean(row.get("多機能トイレ数"))
    if multi:
        add_note(out, "多機能トイレ数", multi)

    return finish(out)


def normalize_shunan(row):
    out = {k: "" for k in STANDARD}

    for key in STANDARD:
        if key in row:
            out[key] = RowSupport.clean(row.get(key))

    # 名称上、標準のバリアフリートイレ数と明確に対応。
    out["バリアフリートイレ数"] = RowSupport.clean(
        row.get("バリアフリー（多目的）トイレ数")
    )

    # 数値 → 有無への変換は行わない。
    out["車椅子使用者用トイレ有無"] = ""
    out["オストメイト設置トイレ有無"] = ""

    for key in SHUNAN_EXTRAS:
        value = RowSupport.clean(row.get(key))
        if value != "":
            add_note(out, key, value)

    return finish(out)


def write_dataset(municipality, rows):
    dest = (
        ROOT
        / "data/normalized/35-山口県"
        / municipality
        / "public-toilet/public-toilet.csv"
    )
    WRITER.write(dest, STANDARD, rows)


def main() -> None:
    total = 0

    for municipality, filename in FILES.items():
        if municipality not in TARGETS:
            continue

        src = (
            ROOT
            / "data/raw/35-山口県"
            / municipality
            / "public-toilet"
            / filename
        )

        source_rows, encoding = read_csv(src, municipality)

        normalized = []

        for row in source_rows:
            if municipality == "35202-宇部市":
                out = normalize_ube(row)
                kind = "custom4"

            elif municipality == "35206-防府市":
                out = normalize_hofu(row)
                kind = "legacy33"

            elif municipality in {
                "35212-柳井市",
                "35213-美祢市",
                "35343-田布施町",
            }:
                out = normalize_old32(row)
                kind = "legacy32"

            elif municipality == "35215-周南市":
                out = normalize_shunan(row)
                kind = "extended49"

            else:
                out = normalize_current(row, municipality)
                kind = "current39"

            normalized.append(out)

        # 周南市は原典で同一IDが異なる2施設に重複している。
        # 新しいIDは生成せず、重複するIDを空欄にして原値を備考へ保存する。
        if municipality == "35215-周南市":
            id_counts = {}
            for out in normalized:
                value = RowSupport.clean(out["ID"])
                if value:
                    id_counts[value] = id_counts.get(value, 0) + 1

            duplicate_ids = {
                value for value, count in id_counts.items()
                if count > 1
            }

            for out in normalized:
                value = RowSupport.clean(out["ID"])
                if value in duplicate_ids:
                    add_note(out, "ID_原値", value)
                    out["ID"] = ""

        write_dataset(municipality, normalized)

        total += len(normalized)

        print(
            f"{municipality} "
            f"source={len(source_rows)} "
            f"normalized={len(normalized)} "
            f"type={kind} "
            f"encoding={encoding}"
        )

    print(f"total normalized: {total}")


if __name__ == "__main__":
    main()
