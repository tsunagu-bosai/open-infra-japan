#!/usr/bin/env python3

import csv
from pathlib import Path
from openpyxl import load_workbook

from schema import FIELDS

ROOT = Path(__file__).resolve().parents[3]

INPUT = (
    ROOT
    / "data/raw/14-神奈川県/barrier-free"
    / "kanagawa-barrier-free.xlsx"
)

OUTPUT = (
    ROOT
    / "data/normalized/14-神奈川県/barrier-free"
    / "kanagawa-barrier-free.csv"
)

SOURCE_NAME = "神奈川県バリアフリー適合施設オープンデータ"
SOURCE_URL = "https://www.pref.kanagawa.jp/docs/n7j/barrierfreeopendata.html"

MUNICIPALITY_CODES = {
    "横浜市": "14100",
    "川崎市": "14130",
    "相模原市": "14150",
    "横須賀市": "14201",
    "平塚市": "14203",
    "鎌倉市": "14204",
    "藤沢市": "14205",
    "小田原市": "14206",
    "茅ヶ崎市": "14207",
    "逗子市": "14208",
    "三浦市": "14210",
    "秦野市": "14211",
    "厚木市": "14212",
    "大和市": "14213",
    "伊勢原市": "14214",
    "海老名市": "14215",
    "座間市": "14216",
    "南足柄市": "14217",
    "綾瀬市": "14218",
    "葉山町": "14301",
    "寒川町": "14321",
    "大磯町": "14341",
    "二宮町": "14342",
    "中井町": "14361",
    "大井町": "14362",
    "松田町": "14363",
    "山北町": "14364",
    "開成町": "14366",
    "箱根町": "14382",
    "真鶴町": "14383",
    "湯河原町": "14384",
    "愛川町": "14401",
    "清川村": "14402",
}

FACILITY_TYPES = {
    1: "官公庁施設",
    2: "教育文化施設",
    3: "医療施設",
    4: "福祉施設",
    5: "商業施設",
    6: "公共交通機関の施設",
    7: "駐車場",
    8: "共同住宅",
    9: "事務所",
    10: "宿泊施設",
    11: "公衆浴場",
    12: "地下街等",
    13: "運動施設",
    14: "興行・遊興施設",
    15: "展示施設",
    16: "工場",
    17: "公衆便所",
    18: "複合用途建築物",
}

STATUS = {
    1: "全項目適合",
    2: "条例13条ただし書き適用",
    3: "みんなのトイレ整備",
}


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def state(value):
    if value in (1, "1"):
        return "yes"
    if value in (0, "0"):
        return "no"
    if value in (9, "9"):
        return "unknown"
    if value in (None, ""):
        return ""
    raise ValueError(f"unexpected state value: {value!r}")


def municipality_from_address(address):
    normalized = clean(address).replace("平塚市", "平塚市")

    for name, code in MUNICIPALITY_CODES.items():
        if name in normalized:
            return code, name

    raise ValueError(f"municipality not found: {address!r}")


def main():
    wb = load_workbook(INPUT, read_only=True, data_only=True)
    ws = wb.active

    rows = ws.iter_rows(values_only=True)
    next(rows)  # header

    output_rows = []

    for source_row, row in enumerate(rows, start=2):
        if not any(v not in (None, "") for v in row):
            continue

        municipality_code, municipality_name = municipality_from_address(row[4])

        facil_type = row[1]

        if isinstance(facil_type, str):
            type_codes = [
                part.strip()
                for part in facil_type.replace(",", "、").split("、")
                if part.strip()
            ]
        else:
            type_codes = [facil_type]

        categories = []

        for code in type_codes:
            try:
                code = int(code)
            except (TypeError, ValueError):
                raise ValueError(
                    f"invalid facil_type at row {source_row}: {facil_type!r}"
                )

            category_name = FACILITY_TYPES.get(code)
            if not category_name:
                raise ValueError(
                    f"unknown facil_type code at row {source_row}: {code!r}"
                )

            categories.append(category_name)

        category = " / ".join(categories)

        status_value = row[7]
        status_text = STATUS.get(status_value, "")
        if not status_text:
            raise ValueError(
                f"unknown status at row {source_row}: {status_value!r}"
            )

        date_value = row[2]
        if hasattr(date_value, "strftime"):
            source_updated_at = date_value.strftime("%Y-%m-%d")
        else:
            source_updated_at = clean(date_value)

        attribute_notes = [
            f"facil_id={clean(row[0])}",
            f"status={status_text}",
        ]

        out = {
            "prefecture_code": "14",
            "prefecture_name": "神奈川県",
            "municipality_code": municipality_code,
            "municipality_name": municipality_name,
            "ward_name": "",

            "facility_name": clean(row[3]),
            "formal_name": "",
            "facility_category": category,
            "postal_code": "",
            "address": clean(row[4]),
            "latitude": "",
            "longitude": "",
            "homepage_url": "",

            "multipurpose_toilet": state(row[5]),
            "wheelchair_toilet": "",
            "toilet_floor": "",
            "unisex_toilet_count": "",
            "male_toilet_count": "",
            "female_toilet_count": "",

            "washlet": "",
            "adult_bed": "",
            "ostomate": state(row[6]),
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

            "source_dataset": "barrier_free_compliance_facilities",
            "source_name": SOURCE_NAME,
            "source_url": SOURCE_URL,
            "source_updated_at": source_updated_at,
            "source_row": str(source_row),
            "attribute_note": " | ".join(attribute_notes),
            "note": clean(row[8]),
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

    print("input rows :", len(output_rows))
    print("output rows:", len(output_rows))
    print("output     :", OUTPUT)


if __name__ == "__main__":
    main()
