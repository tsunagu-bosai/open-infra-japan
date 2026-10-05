#!/usr/bin/env python3

import csv
import re
import unicodedata
from pathlib import Path

from openpyxl import load_workbook

from schema import FIELDS

ROOT = Path(__file__).resolve().parents[3]

INPUT = (
    ROOT
    / "data/raw/09-栃木県/barrier-free"
    / "tochigi-ostomate.xlsx"
)

OUTPUT = (
    ROOT
    / "data/normalized/09-栃木県/barrier-free"
    / "tochigi-ostomate.csv"
)

SOURCE_NAME = "栃木県 オストメイト対応トイレ一覧表"
SOURCE_URL = (
    "https://www.pref.tochigi.lg.jp/e05/welfare/shougaisha/"
    "fukushi/documents/20260805165831.pdf"
)
SOURCE_UPDATED_AT = "2026-05-01"
SOURCE_PROCESSING_NOTE = (
    "source_processing=栃木県公式PDFをAdobe AcrobatでExcelへ変換。"
    "変換後の元データをsheet1に保持し、正規化処理のためsheet2・sheet3へ手作業で整理。"
    "normalized CSVはsheet2・sheet3から生成"
)

MUNICIPALITIES = {
    "宇都宮市": ("09", "栃木県", "09201"),
    "足利市": ("09", "栃木県", "09202"),
    "栃木市": ("09", "栃木県", "09203"),
    "佐野市": ("09", "栃木県", "09204"),
    "鹿沼市": ("09", "栃木県", "09205"),
    "日光市": ("09", "栃木県", "09206"),
    "小山市": ("09", "栃木県", "09208"),
    "真岡市": ("09", "栃木県", "09209"),
    "大田原市": ("09", "栃木県", "09210"),
    "矢板市": ("09", "栃木県", "09211"),
    "那須塩原市": ("09", "栃木県", "09213"),
    "さくら市": ("09", "栃木県", "09214"),
    "那須烏山市": ("09", "栃木県", "09215"),
    "下野市": ("09", "栃木県", "09216"),
    "上三川町": ("09", "栃木県", "09301"),
    "益子町": ("09", "栃木県", "09342"),
    "茂木町": ("09", "栃木県", "09343"),
    "市貝町": ("09", "栃木県", "09344"),
    "芳賀町": ("09", "栃木県", "09345"),
    "壬生町": ("09", "栃木県", "09361"),
    "野木町": ("09", "栃木県", "09364"),
    "塩谷町": ("09", "栃木県", "09384"),
    "高根沢町": ("09", "栃木県", "09386"),
    "那須町": ("09", "栃木県", "09407"),
    "那珂川町": ("09", "栃木県", "09411"),
    "鉾田市": ("08", "茨城県", "08234"),
}

FACILITY_MUNICIPALITY = {
    # JR東日本
    "宇都宮駅": "宇都宮市",
    "雀宮駅": "宇都宮市",
    "小山駅": "小山市",
    "自治医大駅": "下野市",
    "野木駅": "野木町",
    "間々田駅": "小山市",
    "小金井駅": "下野市",
    "那須塩原駅": "那須塩原市",
    "西那須野駅": "那須塩原市",
    "黒磯駅": "那須塩原市",
    "矢板駅": "矢板市",
    "日光駅": "日光市",
    "栃木駅": "栃木市",
    "佐野駅": "佐野市",
    "足利駅": "足利市",
    "鹿沼駅": "鹿沼市",

    # 東武鉄道
    "東武宇都宮駅": "宇都宮市",
    "足利市駅": "足利市",
    "新栃木駅": "栃木市",
    "鬼怒川温泉駅": "日光市",
    "鬼怒川公園駅": "日光市",
    "東武日光駅": "日光市",
    "東武鬼怒川温泉駅": "日光市",
    "東武鬼怒川公園駅": "日光市",

    # NEXCO東日本
    "佐野SA": "佐野市",
    "大谷PA": "宇都宮市",
    "壬生PA": "壬生町",
    "那須高原SA": "那須町",
}


def clean(value):
    if value is None:
        return ""
    return " ".join(str(value).replace("\n", " ").split())


def nfkc(value):
    return unicodedata.normalize("NFKC", clean(value))


def strip_mark(name):
    return clean(name).replace("※", "").strip()


def ostomate_attributes(source_name):
    if "※" in source_name:
        return "", "ostomate_type=simple_pouch_washing_faucet"

    return (
        "yes",
        "ostomate_type=multipurpose_toilet_with_waste_sink",
    )


def municipality_info(name):
    name = clean(name)
    normalized = (
        name
        .replace(" ", "")
        .replace("\u3000", "")
        .replace("(茨城県)", "")
        .strip()
    )

    if normalized not in MUNICIPALITIES:
        raise ValueError(f"unknown municipality: {name!r}")

    return normalized, MUNICIPALITIES[normalized]


def municipality_from_address(address):
    compact = nfkc(address).replace(" ", "")

    for muni in sorted(MUNICIPALITIES, key=len, reverse=True):
        if muni in compact:
            return muni

    return ""


def base_record(
    municipality,
    facility_name,
    address,
    source_row,
    operator="",
):
    muni_name, (pref_code, pref_name, muni_code) = municipality_info(
        municipality
    )

    multipurpose, type_note = ostomate_attributes(facility_name)

    notes = [SOURCE_PROCESSING_NOTE]
    if operator:
        notes.append(f"operator={operator}")

    return {
        "prefecture_code": pref_code,
        "prefecture_name": pref_name,
        "municipality_code": muni_code,
        "municipality_name": muni_name,
        "ward_name": "",

        "facility_name": strip_mark(facility_name),
        "formal_name": "",
        "facility_category": "",
        "postal_code": "",
        "address": clean(address),
        "latitude": "",
        "longitude": "",
        "homepage_url": "",

        "multipurpose_toilet": multipurpose,
        "wheelchair_toilet": "",
        "toilet_floor": "",
        "unisex_toilet_count": "",
        "male_toilet_count": "",
        "female_toilet_count": "",

        "washlet": "",
        "adult_bed": "",
        "ostomate": "yes",
        "voice_guidance": "",
        "baby_bed": "",
        "baby_chair": "",
        "child_toilet": "",
        "child_chair": "",
        "flush_type": "",
        "emergency_call_type": "",

        "male_urinal_with_rail": "",
        "male_western_toilet": "",
        "female_western_toilet": "",
        "male_baby_bed": "",
        "female_baby_bed": "",
        "male_baby_chair": "",
        "female_baby_chair": "",

        "entrance_step": "",
        "stroller_rental": "",
        "nursing_space": "",
        "diaper_changing_space": "",
        "kids_room": "",

        "source_dataset": "ostomate_toilet_list",
        "source_name": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "source_updated_at": SOURCE_UPDATED_AT,
        "source_row": source_row,
        "attribute_note": type_note,
        "note": " | ".join(notes),
    }


def parse_road_station(value):
    value = clean(value)

    m = re.match(r"^(.*?)（(.+)）$", value)
    if not m:
        raise ValueError(f"cannot parse road station: {value!r}")

    name = m.group(1).strip()
    address = m.group(2).strip()

    municipality = municipality_from_address(address)
    if not municipality:
        raise ValueError(
            f"municipality not found for road station: "
            f"{name!r}, {address!r}"
        )

    return name, address, municipality


def main():
    wb = load_workbook(INPUT, data_only=True, read_only=True)

    ws2 = wb["sheet2"]
    ws3 = wb["sheet3"]

    output_rows = []

    # sheet2: 通常施設一覧
    for rownum, row in enumerate(
        ws2.iter_rows(min_row=2, values_only=True),
        start=2,
    ):
        no, municipality, name, address, *_ = row

        if not name:
            continue

        municipality = clean(municipality)
        name = clean(name)
        address = clean(address)

        if municipality == "鉾田市 (茨城県)":
            municipality = "鉾田市"

        output_rows.append(
            base_record(
                municipality=municipality,
                facility_name=name,
                address=address,
                source_row=f"sheet2:{rownum}",
            )
        )

    # sheet3: 事業者別一覧
    for rownum, row in enumerate(
        ws3.iter_rows(min_row=2, values_only=True),
        start=2,
    ):
        no, operator, value, *_ = row

        if not value:
            continue

        operator = clean(operator)
        value = clean(value)

        if operator in ("JR 東日本", "東武鉄道", "NEXCO 東日本"):
            facilities = [
                x.strip()
                for x in re.split(r"[、,]", value)
                if x.strip()
            ]

            for idx, source_name in enumerate(facilities, 1):
                lookup_name = nfkc(strip_mark(source_name))

                municipality = FACILITY_MUNICIPALITY.get(lookup_name)
                if not municipality:
                    raise ValueError(
                        f"municipality not found: "
                        f"{operator=} {source_name=}"
                    )

                output_rows.append(
                    base_record(
                        municipality=municipality,
                        facility_name=source_name,
                        address="",
                        source_row=f"sheet3:{rownum}:{idx}",
                        operator=operator,
                    )
                )

        elif operator == "道の駅":
            source_name, address, municipality = parse_road_station(value)

            output_rows.append(
                base_record(
                    municipality=municipality,
                    facility_name=source_name,
                    address=address,
                    source_row=f"sheet3:{rownum}",
                    operator=operator,
                )
            )

        else:
            raise ValueError(
                f"unknown operator at sheet3:{rownum}: {operator!r}"
            )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(output_rows)

    print("sheet2 rows:", 278)
    print("output rows:", len(output_rows))
    print("output     :", OUTPUT)


if __name__ == "__main__":
    main()
