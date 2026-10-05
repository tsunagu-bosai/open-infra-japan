#!/usr/bin/env python3

import csv
from pathlib import Path

from schema import FIELDS

ROOT = Path(__file__).resolve().parents[3]

INPUT = Path("/tmp/saga-barrier-free-converted.csv")

OUTPUT = (
    ROOT
    / "data/normalized/41-佐賀県/barrier-free"
    / "saga-barrier-free.csv"
)

SOURCE_NAME = "佐賀県 みんなのトイレ"
SOURCE_URL = "https://www.pref.saga.lg.jp/kiji00375898/index.html"
SOURCE_UPDATED_AT = "2023-08-01"

MUNICIPALITY_CODES = {
    "佐賀市": "41201",
    "唐津市": "41202",
    "鳥栖市": "41203",
    "多久市": "41204",
    "伊万里市": "41205",
    "武雄市": "41206",
    "鹿島市": "41207",
    "小城市": "41208",
    "嬉野市": "41209",
    "神埼市": "41210",
    "吉野ヶ里町": "41327",
    "基山町": "41341",
    "上峰町": "41345",
    "みやき町": "41346",
    "玄海町": "41387",
    "有田町": "41401",
    "大町町": "41423",
    "江北町": "41424",
    "白石町": "41425",
    "太良町": "41441",
}

SOURCE_TYPE_NAME = {
    "private": "民間施設",
    "municipal": "市町施設",
    "prefectural": "県有施設",
}


def yn(value):
    if value in ("○", "〇"):
        return "yes"
    if value in ("－", "-"):
        return "no"
    if value == "":
        return ""
    raise ValueError(f"unexpected mark: {value!r}")


def main():
    with INPUT.open(
        encoding="utf-8",
        newline="",
    ) as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 1032

    output_rows = []

    for r in rows:
        municipality = r["municipality"]
        municipality_code = MUNICIPALITY_CODES.get(municipality)

        if not municipality_code:
            raise ValueError(
                f"unknown municipality: {municipality!r}"
            )

        toilet_type = r["toilet_type"]

        if toilet_type == "多機能":
            multipurpose_toilet = "yes"
        elif toilet_type in ("車いす", "一般ﾄｲﾚ", "一般トイレ"):
            multipurpose_toilet = "no"
        else:
            raise ValueError(
                f"unexpected toilet type: {toilet_type!r}"
            )

        wheelchair_toilet = yn(r["wheelchair"])
        ostomate = yn(r["ostomate"])
        baby_bed = yn(r["baby_bed"])
        baby_chair = yn(r["baby_chair"])

        attribute_note = (
            f"source_type={SOURCE_TYPE_NAME[r['source_type']]}; "
            f"toilet_type={toilet_type}"
        )

        out = {
            "prefecture_code": "41",
            "prefecture_name": "佐賀県",
            "municipality_code": municipality_code,
            "municipality_name": municipality,
            "ward_name": "",

            "facility_name": r["facility"],
            "formal_name": "",
            "facility_category": "",
            "postal_code": "",
            "address": r["address"],
            "latitude": "",
            "longitude": "",
            "homepage_url": "",

            "multipurpose_toilet": multipurpose_toilet,
            "wheelchair_toilet": wheelchair_toilet,
            "toilet_floor": "",
            "unisex_toilet_count": "",
            "male_toilet_count": "",
            "female_toilet_count": "",

            "washlet": "",
            "adult_bed": "",
            "ostomate": ostomate,
            "voice_guidance": "",
            "baby_bed": baby_bed,
            "baby_chair": baby_chair,
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

            "source_dataset": "everyone_toilet",
            "source_name": SOURCE_NAME,
            "source_url": SOURCE_URL,
            "source_updated_at": SOURCE_UPDATED_AT,
            "source_row": (
                f"{r['source_type']}:{r['source_line']}"
            ),
            "attribute_note": attribute_note,
            "note": "",
        }

        output_rows.append(out)

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(output_rows)

    print("input rows :", len(rows))
    print("output rows:", len(output_rows))
    print("output     :", OUTPUT)


if __name__ == "__main__":
    main()
