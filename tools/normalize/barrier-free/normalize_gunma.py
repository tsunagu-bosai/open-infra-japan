#!/usr/bin/env python3

import csv
from pathlib import Path
from openpyxl import load_workbook

from schema import FIELDS

ROOT = Path(__file__).resolve().parents[3]

INPUT = (
    ROOT
    / "data/raw/10-群馬県/barrier-free"
    / "gunma-ostomate-universal-sheet.xlsx"
)

OUTPUT = (
    ROOT
    / "data/normalized/10-群馬県/barrier-free"
    / "gunma-ostomate-universal-sheet.csv"
)

SOURCE_NAME = "群馬県 オストメイト対応トイレ・ユニバーサルシート設置施設一覧"
SOURCE_URL = "https://www.pref.gunma.jp/site/fukushinomachi/3013.html"
SOURCE_UPDATED_AT = "2025"

MUNICIPALITY_CODES = {
    "前橋市": "10201",
    "高崎市": "10202",
    "桐生市": "10203",
    "伊勢崎市": "10204",
    "太田市": "10205",
    "沼田市": "10206",
    "館林市": "10207",
    "渋川市": "10208",
    "藤岡市": "10209",
    "富岡市": "10210",
    "安中市": "10211",
    "みどり市": "10212",
    "榛東村": "10344",
    "吉岡町": "10345",
    "上野村": "10366",
    "神流町": "10367",
    "下仁田町": "10382",
    "南牧村": "10383",
    "甘楽町": "10384",
    "中之条町": "10421",
    "長野原町": "10424",
    "嬬恋村": "10425",
    "草津町": "10426",
    "高山村": "10428",
    "東吾妻町": "10429",
    "片品村": "10443",
    "川場村": "10444",
    "昭和村": "10448",
    "みなかみ町": "10449",
    "玉村町": "10464",
    "板倉町": "10521",
    "明和町": "10522",
    "千代田町": "10523",
    "大泉町": "10524",
    "邑楽町": "10525",
}


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def facility_state(value):
    value = clean(value)

    if not value:
        return ""

    if value == "－":
        return "no"

    return "yes"


def main():
    wb = load_workbook(INPUT, read_only=True, data_only=True)
    ws = wb.active

    rows = ws.iter_rows(values_only=True)

    # 1行目空行、2行目ヘッダ
    next(rows)
    headers = next(rows)

    output_rows = []

    for source_row, row in enumerate(rows, start=3):
        values = row[:11]

        if not any(v not in (None, "") for v in values):
            continue

        municipality_name = clean(row[1])
        municipality_code = MUNICIPALITY_CODES.get(municipality_name)

        if not municipality_code:
            raise ValueError(
                f"unknown municipality at row {source_row}: "
                f"{municipality_name!r}"
            )

        ostomate_location = clean(row[5])
        universal_sheet_location = clean(row[6])

        attribute_notes = []

        if ostomate_location and ostomate_location != "－":
            attribute_notes.append(
                f"ostomate_location={ostomate_location}"
            )

        if universal_sheet_location and universal_sheet_location != "－":
            attribute_notes.append(
                f"universal_sheet_location={universal_sheet_location}"
            )

        phone = clean(row[4])
        opening_hours = clean(row[7])
        owner = clean(row[9])
        department = clean(row[10])

        notes = []

        if phone:
            notes.append(f"phone={phone}")

        if opening_hours:
            notes.append(f"opening_hours={opening_hours}")

        if owner:
            notes.append(f"owner={owner}")

        if department:
            notes.append(f"department={department}")

        source_note = clean(row[8])
        if source_note:
            notes.append(source_note)

        out = {
            "prefecture_code": "10",
            "prefecture_name": "群馬県",
            "municipality_code": municipality_code,
            "municipality_name": municipality_name,
            "ward_name": "",

            "facility_name": clean(row[2]),
            "formal_name": "",
            "facility_category": "",
            "postal_code": "",
            "address": clean(row[3]),
            "latitude": "",
            "longitude": "",
            "homepage_url": "",

            "multipurpose_toilet": "",
            "wheelchair_toilet": "",
            "toilet_floor": "",
            "unisex_toilet_count": "",
            "male_toilet_count": "",
            "female_toilet_count": "",

            "washlet": "",
            "adult_bed": facility_state(universal_sheet_location),
            "ostomate": facility_state(ostomate_location),
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

            "source_dataset": "ostomate_universal_sheet_list",
            "source_name": SOURCE_NAME,
            "source_url": SOURCE_URL,
            "source_updated_at": SOURCE_UPDATED_AT,
            "source_row": str(source_row),
            "attribute_note": " | ".join(attribute_notes),
            "note": " | ".join(notes),
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
