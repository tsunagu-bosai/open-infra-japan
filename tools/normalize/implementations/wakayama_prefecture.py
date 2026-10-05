#!/usr/bin/env python3

import csv
import re
import unicodedata
from pathlib import Path
from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.normalization import RowSupport

ROOT = Path(__file__).resolve().parents[3]

SOURCE = (
    ROOT
    / "data/raw/30-和歌山県/30000-和歌山県/public-toilet"
    / "300004_062500_kankoutitoire.csv"
)

MASTER = ROOT / "data/reference/municipalities.csv"

# この県CSVを導入する以前から cataloged 済み。
# 既存データを上書きしない。
SKIP_CODES = {
    "30201",  # 和歌山市
    "30202",  # 海南市
    "30304",  # 紀美野町
}

FIELDS = [
    "全国地方公共団体コード",
    "ID",
    "地方公共団体名",
    "名称",
    "名称_カナ",
    "名称_英語",
    "所在地_全国地方公共団体コード",
    "町字ID",
    "所在地_連結表記",
    "所在地_都道府県",
    "所在地_市区町村",
    "所在地_町字",
    "所在地_番地以下",
    "建物名等(方書)",
    "設置位置",
    "緯度",
    "経度",
    "高度の種別",
    "高度の値",
    "男性トイレ総数",
    "男性トイレ数（小便器）",
    "男性トイレ数（和式）",
    "男性トイレ数（洋式）",
    "女性トイレ総数",
    "女性トイレ数（和式）",
    "女性トイレ数（洋式）",
    "男女共用トイレ総数",
    "男女共用トイレ数（和式）",
    "男女共用トイレ数（洋式）",
    "バリアフリートイレ数",
    "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無",
    "利用開始時間",
    "利用終了時間",
    "利用可能時間特記事項",
    "画像",
    "画像_ライセンス",
    "備考",
]



def exact_integer(value):
    """純粋な整数だけ採用。1(1) 等は解釈しない。"""
    value = RowSupport.clean(value)
    if re.fullmatch(r"\d+", value):
        return value
    return ""


def parse_time_range(value):
    """
    単純な HH:MM～HH:MM だけ開始・終了に分離。
    終日、開館時、注記付き等は特記事項に残す。
    """
    original = RowSupport.clean(value)
    if not original:
        return "", "", ""

    s = unicodedata.normalize("NFKC", original)
    s = s.replace("〜", "~").replace("～", "~")

    m = re.fullmatch(
        r"\s*(\d{1,2}):(\d{2})\s*~\s*(\d{1,2}):(\d{2})\s*",
        s,
    )

    if not m:
        return "", "", original

    h1, m1, h2, m2 = map(int, m.groups())

    if not (
        0 <= h1 <= 23
        and 0 <= h2 <= 23
        and 0 <= m1 <= 59
        and 0 <= m2 <= 59
    ):
        return "", "", original

    return (
        f"{h1:02d}:{m1:02d}",
        f"{h2:02d}:{m2:02d}",
        "",
    )


def has_any(row, keys):
    return any(RowSupport.clean(row.get(k)) for k in keys)


def add_note(notes, label, value):
    value = RowSupport.clean(value)
    if value:
        notes.append(f"{label}:{value}")


def normalize_source_row(raw):
    # 末尾全角空白を除去したキーで扱う。
    row = {RowSupport.clean(k): v for k, v in raw.items()}

    # 現況写真は見出し内に全角空白があるためprefixで取得。
    photo_status = ""
    for key, value in row.items():
        if key.startswith("現況写真"):
            photo_status = RowSupport.clean(value)
            break

    return row, photo_status


def main():
    with MASTER.open(encoding="utf-8-sig", newline="") as f:
        master_rows = list(csv.DictReader(f))

    name_to_code = {
        RowSupport.clean(r["municipality_name"]): RowSupport.clean(r["municipality_code"])
        for r in master_rows
        if RowSupport.clean(r["prefecture_code"]) == "30"
    }

    with SOURCE.open(encoding="utf-8-sig", newline="") as f:
        source_rows = list(csv.DictReader(f))

    outputs = {}
    skipped = 0

    for raw in source_rows:
        row, photo_status = normalize_source_row(raw)

        municipality_name = RowSupport.clean(row.get("市町村名"))
        code5 = name_to_code.get(municipality_name, "")

        if not code5:
            raise ValueError(
                f"municipality not resolved: {municipality_name!r}"
            )

        if code5 in SKIP_CODES:
            skipped += 1
            continue

        code6 = six_digit_municipality_code(code5)

        facility_name = RowSupport.clean(row.get("トイレ名"))
        source_id = RowSupport.clean(row.get("№"))
        address = RowSupport.clean(row.get("住所"))

        if not source_id:
            raise ValueError(
                f"blank source id: {municipality_name} {facility_name}"
            )

        if not facility_name:
            raise ValueError(
                f"blank facility name: {municipality_name} №{source_id}"
            )

        start_time, end_time, time_note = parse_time_range(
            row.get("利用可能時間")
        )

        male_urinal_raw = RowSupport.clean(
            row.get("一般トイレ設備内容・男性用トイレ・小便器")
        )
        male_jp_raw = RowSupport.clean(
            row.get("一般トイレ設備内容・男性用トイレ・和式")
        )
        male_west_raw = RowSupport.clean(
            row.get("一般トイレ設備内容・男性用トイレ・洋式")
        )
        female_jp_raw = RowSupport.clean(
            row.get("一般トイレ設備内容・女性用トイレ・和式")
        )
        female_west_raw = RowSupport.clean(
            row.get("一般トイレ設備内容・女性用トイレ・洋式")
        )

        infant_keys = [
            "多目的トイレ設備内容・ベビーベッド",
            "多目的トイレ設備内容・ベビーチェア",
            "一般トイレ設備内容・男性用トイレ・ベビーベッド",
            "一般トイレ設備内容・男性用トイレ・ベビーチェア",
            "一般トイレ設備内容・女性用トイレ・ベビーベッド",
            "一般トイレ設備内容・女性用トイレ・ベビーチェア",
        ]

        ostomate_raw = RowSupport.clean(
            row.get("多目的トイレ設備内容・オストメイト洗浄")
        )

        infant_flag = "有" if has_any(row, infant_keys) else ""
        ostomate_flag = "有" if ostomate_raw else ""

        notes = []

        # 元資料で標準列へ安全に変換できない情報を保持。
        note_fields = [
            ("現況写真", photo_status),
            (
                "一般利用者用駐車場・無料",
                row.get("一般利用者用駐車場・無料"),
            ),
            (
                "一般利用者用駐車場・有料",
                row.get("一般利用者用駐車場・有料"),
            ),
            ("障害者用駐車場", row.get("障害者用駐車場")),
            ("駐車場スペース", row.get("駐車場スペース")),
            (
                "多目的トイレ設備内容・洋式",
                row.get("多目的トイレ設備内容・洋式"),
            ),
            (
                "多目的トイレ設備内容・ベビーベッド",
                row.get("多目的トイレ設備内容・ベビーベッド"),
            ),
            (
                "多目的トイレ設備内容・ベビーチェア",
                row.get("多目的トイレ設備内容・ベビーチェア"),
            ),
            (
                "多目的トイレ設備内容・介護用ベッド",
                row.get("多目的トイレ設備内容・介護用ベッド"),
            ),
            (
                "多目的トイレ設備内容・温水洗浄洗浄",
                row.get("多目的トイレ設備内容・温水洗浄洗浄"),
            ),
            (
                "多目的トイレ設備内容・オストメイト洗浄",
                ostomate_raw,
            ),
            (
                "男性温水洗浄便座",
                row.get("一般トイレ設備内容・男性用トイレ・温水洗浄便座"),
            ),
            (
                "男性荷物置き場",
                row.get("一般トイレ設備内容・男性用トイレ・荷物置き場"),
            ),
            (
                "男性ベビーベッド",
                row.get("一般トイレ設備内容・男性用トイレ・ベビーベッド"),
            ),
            (
                "男性ベビーチェア",
                row.get("一般トイレ設備内容・男性用トイレ・ベビーチェア"),
            ),
            (
                "男性音姫",
                row.get("一般トイレ設備内容・男性用トイレ・音姫"),
            ),
            (
                "女性温水洗浄便座",
                row.get("一般トイレ設備内容・女性用トイレ・温水洗浄便座"),
            ),
            (
                "女性小便器",
                row.get("一般トイレ設備内容・女性用トイレ・小便器"),
            ),
            (
                "女性荷物置き場",
                row.get("一般トイレ設備内容・女性用トイレ・荷物置き場"),
            ),
            (
                "女性ベビーベッド",
                row.get("一般トイレ設備内容・女性用トイレ・ベビーベッド"),
            ),
            (
                "女性ベビーチェア",
                row.get("一般トイレ設備内容・女性用トイレ・ベビーチェア"),
            ),
            (
                "女性音姫",
                row.get("一般トイレ設備内容・女性用トイレ・音姫"),
            ),
            ("設備備考", row.get("設備備考")),
        ]

        for label, value in note_fields:
            add_note(notes, label, value)

        # 括弧付き等で標準の「個数」に安全変換できなかった値も保持。
        count_fields = [
            ("男性小便器原値", male_urinal_raw),
            ("男性和式原値", male_jp_raw),
            ("男性洋式原値", male_west_raw),
            ("女性和式原値", female_jp_raw),
            ("女性洋式原値", female_west_raw),
        ]

        for label, value in count_fields:
            if value and not exact_integer(value):
                add_note(notes, label, value)

        out = {field: "" for field in FIELDS}

        out.update({
            "全国地方公共団体コード": code6,
            "ID": source_id,
            "地方公共団体名": municipality_name,
            "名称": facility_name,
            "所在地_全国地方公共団体コード": code6,
            "所在地_連結表記": address,
            "所在地_都道府県": "和歌山県",
            "所在地_市区町村": municipality_name,
            "緯度": RowSupport.clean(row.get("緯度")),
            "経度": RowSupport.clean(row.get("経度")),

            # 総数は元資料に直接存在しないので推計しない。
            "男性トイレ数（小便器）": exact_integer(male_urinal_raw),
            "男性トイレ数（和式）": exact_integer(male_jp_raw),
            "男性トイレ数（洋式）": exact_integer(male_west_raw),
            "女性トイレ数（和式）": exact_integer(female_jp_raw),
            "女性トイレ数（洋式）": exact_integer(female_west_raw),

            # 多目的洋式便器数からバリアフリートイレ数は推定しない。
            "バリアフリートイレ数": "",

            # 障害者用駐車場から車椅子対応トイレを推定しない。
            "車椅子使用者用トイレ有無": "",
            "乳幼児用設備設置トイレ有無": infant_flag,
            "オストメイト設置トイレ有無": ostomate_flag,

            "利用開始時間": start_time,
            "利用終了時間": end_time,
            "利用可能時間特記事項": time_note,

            # 現況写真はURLではなく「あり/なし」等なので画像欄へ入れない。
            "画像": "",
            "画像_ライセンス": "",
            "備考": " / ".join(notes),
        })

        outputs.setdefault((code5, municipality_name), []).append(out)

    total = 0

    for (code5, municipality_name), rows in sorted(outputs.items()):
        outdir = (
            ROOT
            / "data/normalized/30-和歌山県"
            / f"{code5}-{municipality_name}"
            / "public-toilet"
        )
        outdir.mkdir(parents=True, exist_ok=True)

        outfile = outdir / "public-toilet.csv"

        with outfile.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=FIELDS,
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)

        print(f"{code5} {municipality_name}: {len(rows)}")
        total += len(rows)

    print()
    print("municipalities:", len(outputs))
    print("normalized rows:", total)
    print("skipped existing rows:", skipped)


if __name__ == "__main__":
    main()
