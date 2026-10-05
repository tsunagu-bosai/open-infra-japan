#!/usr/bin/env python3

import csv
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

from schema import FIELDS

ROOT = Path(__file__).resolve().parents[3]

RAW_DIR = ROOT / "data/raw/46-鹿児島県/barrier-free"
INDEX = RAW_DIR / "kagoshima-ostomate-index.csv"
DETAIL_DIR = RAW_DIR / "details"

OUTPUT = (
    ROOT
    / "data/normalized/46-鹿児島県/barrier-free"
    / "kagoshima-ostomate.csv"
)

SOURCE_NAME = "鹿児島県 かごしまバリアフリーマップ オストメイト対応施設"
SOURCE_URL = "https://www.pref.kagoshima.jp/suisuinavi/setsubi_ostomate.html"

MUNICIPALITIES = {
    "鹿児島市": "46201",
    "鹿屋市": "46203",
    "枕崎市": "46204",
    "阿久根市": "46206",
    "出水市": "46208",
    "指宿市": "46210",
    "西之表市": "46213",
    "垂水市": "46214",
    "薩摩川内市": "46215",
    "日置市": "46216",
    "曽於市": "46217",
    "霧島市": "46218",
    "いちき串木野市": "46219",
    "南さつま市": "46220",
    "志布志市": "46221",
    "奄美市": "46222",
    "南九州市": "46223",
    "伊佐市": "46224",
    "姶良市": "46225",
    "三島村": "46303",
    "十島村": "46304",
    "さつま町": "46392",
    "長島町": "46404",
    "湧水町": "46452",
    "大崎町": "46468",
    "東串良町": "46482",
    "錦江町": "46490",
    "南大隅町": "46491",
    "肝付町": "46492",
    "中種子町": "46501",
    "南種子町": "46502",
    "屋久島町": "46505",
    "大和村": "46523",
    "宇検村": "46524",
    "瀬戸内町": "46525",
    "龍郷町": "46527",
    "喜界町": "46529",
    "徳之島町": "46530",
    "天城町": "46531",
    "伊仙町": "46532",
    "和泊町": "46533",
    "知名町": "46534",
    "与論町": "46535",
}

BROKEN_DETAIL_OVERRIDES = {
    "23028": ("46201", "鹿児島市"),
    "2902": ("46505", "屋久島町"),
}


class DetailParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.in_tr = False
        self.current_row = []
        self.in_cell = False
        self.cell_tag = None
        self.cell_buf = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.in_tr = True
            self.current_row = []
        elif self.in_tr and tag in ("th", "td"):
            self.in_cell = True
            self.cell_tag = tag
            self.cell_buf = []
        elif self.in_cell and tag == "br":
            self.cell_buf.append("\n")

    def handle_data(self, data):
        if self.in_cell:
            self.cell_buf.append(data)

    def handle_endtag(self, tag):
        if self.in_cell and tag == self.cell_tag:
            text = "".join(self.cell_buf)
            text = "\n".join(
                " ".join(line.split())
                for line in text.splitlines()
                if " ".join(line.split())
            )
            self.current_row.append((self.cell_tag, text))
            self.in_cell = False
            self.cell_tag = None
            self.cell_buf = []

        elif tag == "tr" and self.in_tr:
            if self.current_row:
                self.rows.append(self.current_row)
            self.current_row = []
            self.in_tr = False


def clean(value):
    return "" if value is None else str(value).strip()


def parse_detail(path):
    parser = DetailParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))

    values = defaultdict(list)

    for row in parser.rows:
        th = [text for tag, text in row if tag == "th" and text]
        td = [text for tag, text in row if tag == "td" and text]

        if not th or not td:
            continue

        values[th[0]].append("\n".join(td))

    return values


def first(values, label):
    vals = values.get(label, [])
    return vals[0] if vals else ""


def municipality_from_address(address):
    for name, code in MUNICIPALITIES.items():
        if name in address:
            return code, name
    return None


def yes_if_present(value):
    return "yes" if clean(value) else ""


def normalize_multipurpose(value):
    value = clean(value)
    if not value:
        return ""

    if "あり" in value or "多目的トイレ" in value:
        return "yes"

    return ""


def has_any(text, patterns):
    return any(p in text for p in patterns)


def stroller_state(value):
    value = clean(value)
    if not value:
        return ""

    if not has_any(value, ("ベビーカー", "バギー")):
        return ""

    if re.search(r"(ベビーカー|バギー)[^。、，,]*なし", value):
        return ""

    return "yes"


def build_attribute_note(values):
    notes = []

    keep_labels = [
        "ふりがな",
        "個室内の寸法",
        "便座の高さ",
        "手すりの高さ",
        "扉の形状・開放幅",
        "洗面台の高さ",
        "鍵の高さ",
        "取っ手の高さ",
        "水道形状",
        "オストメイト対応状況",
        "広いトイレ",
        "非常呼び出しボタン",
        "その他の設備",
        "ベビールームの有無",
        "貸し出し車椅子・ベビーカー",
        "障がい者駐車場スペース",
        "パーキング パーミット 駐車場",
        "駐車場の有無",
        "駐車場の形態",
        "トイレまでのアプローチ",
    ]

    for label in keep_labels:
        for value in values.get(label, []):
            if value:
                notes.append(
                    f"{label}={value.replace(chr(10), ' / ')}"
                )

    for value in values.get("その他", []):
        if value:
            notes.append(
                f"その他={value.replace(chr(10), ' / ')}"
            )

    return " | ".join(notes)


def main():
    with INDEX.open(encoding="utf-8", newline="") as f:
        index_rows = list(csv.DictReader(f))

    output_rows = []

    for index_row_number, item in enumerate(index_rows, start=2):
        facility_id = clean(item["facility_id"])
        index_name = clean(item["facility_name"])
        detail_path = DETAIL_DIR / f"{facility_id}.html"

        if detail_path.exists():
            values = parse_detail(detail_path)

            facility_name = first(values, "施設名") or index_name
            category = first(values, "施設分類")
            address = first(values, "所在地")
            phone = first(values, "電話番号")
            homepage = first(values, "ホームページURL")
            opening_hours = first(values, "開店・営業時間帯")
            closed_days = first(values, "定休日")

            hit = municipality_from_address(address)
            if not hit:
                raise ValueError(
                    f"municipality not found: "
                    f"id={facility_id} name={facility_name!r} "
                    f"address={address!r}"
                )

            municipality_code, municipality_name = hit

            other_equipment = "\n".join(
                values.get("その他の設備", [])
            )
            baby_room = "\n".join(
                values.get("ベビールームの有無", [])
            )
            stroller = "\n".join(
                values.get("貸し出し車椅子・ベビーカー", [])
            )

            multipurpose = normalize_multipurpose(
                first(values, "広いトイレ")
            )

            emergency = (
                "button"
                if first(values, "非常呼び出しボタン")
                else ""
            )

            baby_bed = (
                "yes"
                if has_any(
                    other_equipment,
                    ("ベビーベッド", "ベビーベット"),
                )
                else ""
            )

            baby_chair = (
                "yes"
                if "ベビーキープ" in other_equipment
                else ""
            )

            diaper = (
                "yes"
                if has_any(
                    other_equipment,
                    ("おむつ交換台", "オムツ替えシート"),
                )
                else ""
            )

            adult_bed = (
                "yes"
                if "介助用ベッド" in other_equipment
                else ""
            )

            nursing = (
                "yes"
                if "授乳" in baby_room
                else ""
            )

            notes = []

            if phone:
                notes.append(f"phone={phone}")

            if opening_hours:
                notes.append(
                    f"opening_hours={opening_hours.replace(chr(10), ' / ')}"
                )

            if closed_days:
                notes.append(
                    f"closed_days={closed_days.replace(chr(10), ' / ')}"
                )

            detail_note = ""

        else:
            facility_name = index_name
            category = ""
            address = ""
            homepage = ""
            multipurpose = ""
            emergency = ""
            baby_bed = ""
            baby_chair = ""
            diaper = ""
            adult_bed = ""
            nursing = ""
            stroller = ""
            values = defaultdict(list)

            try:
                municipality_code, municipality_name = (
                    BROKEN_DETAIL_OVERRIDES[facility_id]
                )
            except KeyError:
                raise ValueError(
                    f"detail missing without override: {facility_id}"
                )

            notes = [
                f"detail_page_404={item['url']}",
                f"index_region={item['region']}",
            ]
            detail_note = "detail page unavailable"

        out = {
            "prefecture_code": "46",
            "prefecture_name": "鹿児島県",
            "municipality_code": municipality_code,
            "municipality_name": municipality_name,
            "ward_name": "",

            "facility_name": facility_name,
            "formal_name": "",
            "facility_category": category,
            "postal_code": "",
            "address": address,
            "latitude": "",
            "longitude": "",
            "homepage_url": homepage,

            "multipurpose_toilet": multipurpose,
            "wheelchair_toilet": "",
            "toilet_floor": "",
            "unisex_toilet_count": "",
            "male_toilet_count": "",
            "female_toilet_count": "",

            "washlet": "",
            "adult_bed": adult_bed,
            "ostomate": "yes",
            "voice_guidance": "",
            "baby_bed": baby_bed,
            "baby_chair": baby_chair,
            "child_toilet": "",
            "child_chair": "",
            "flush_type": "",
            "emergency_call_type": emergency,

            "male_urinal_with_rail": "",
            "male_western_toilet": "",
            "female_western_toilet": "",
            "male_baby_bed": "",
            "female_baby_bed": "",
            "male_baby_chair": "",
            "female_baby_chair": "",

            "entrance_step": "",
            "stroller_rental": stroller_state(stroller),
            "nursing_space": nursing,
            "diaper_changing_space": diaper,
            "kids_room": "",

            "source_dataset": "ostomate_facility_map",
            "source_name": SOURCE_NAME,
            "source_url": (
                item["url"]
                if detail_path.exists()
                else SOURCE_URL
            ),
            "source_updated_at": "",
            "source_row": facility_id,
            "attribute_note": build_attribute_note(values),
            "note": " | ".join(notes + ([detail_note] if detail_note else [])),
        }

        output_rows.append(out)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(output_rows)

    print("input rows :", len(index_rows))
    print("output rows:", len(output_rows))
    print("output     :", OUTPUT)


if __name__ == "__main__":
    main()
