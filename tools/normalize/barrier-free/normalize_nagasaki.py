#!/usr/bin/env python3

import csv
import re
from collections import Counter
from pathlib import Path

from schema import FIELDS

ROOT = Path(__file__).resolve().parents[3]

INPUT_TEXT = Path("/tmp/nagasaki-ostomate.txt")

OUTPUT = (
    ROOT
    / "data/normalized/42-長崎県/barrier-free"
    / "nagasaki-ostomate.csv"
)

SOURCE_NAME = "長崎県 オストメイト対応トイレ県内設置場所一覧"
SOURCE_URL = "https://www.pref.nagasaki.jp/uploads/2025/06/1750322278.pdf"

MUNICIPALITIES = {
    "長崎市": "42201",
    "佐世保市": "42202",
    "島原市": "42203",
    "諫早市": "42204",
    "大村市": "42205",
    "平戸市": "42207",
    "松浦市": "42208",
    "対馬市": "42209",
    "壱岐市": "42210",
    "五島市": "42211",
    "西海市": "42212",
    "雲仙市": "42213",
    "南島原市": "42214",
    "長与町": "42307",
    "時津町": "42308",
    "東彼杵町": "42321",
    "川棚町": "42322",
    "波佐見町": "42323",
    "小値賀町": "42383",
    "佐々町": "42391",
    "新上五島町": "42411",
}

OVERRIDES = {
    87: {
        "facility": "西町小学校",
        "note": "※R7.9供用開始予定の新校舎に整備予定",
    },
    88: {
        "facility": "小島小学校",
        "note": "※R５.3月仮設校舎に整備。また、R9.3供用開始予定の新校舎に整備予定",
    },
    89: {
        "facility": "西浦上小学校",
        "note": "※R４.3月仮設校舎に整備。また、R8.4供用開始予定の新校舎に整備予定",
    },
    90: {
        "facility": "琴海中学校",
        "note": "※R9供用開始予定の新校舎に整備予定",
    },
    270: {
        "facility": "松浦市福島地域農水産物等直売施設 とれたて福の島",
        "note": "",
    },
}

SPECIAL_OSTOMATE_UNKNOWN = {
    77,
    87,
    88,
    89,
    90,
    347,
}


def clean(value):
    if value is None:
        return ""
    return " ".join(str(value).replace("\n", " ").split())


def is_note(text):
    return (
        text.startswith("※")
        or text.startswith("（")
        or text.startswith("(")
        or text == "予定"
    )


def parse_records():
    raw_lines = INPUT_TEXT.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    lines = []

    for raw in raw_lines:
        line = raw.replace("\f", "").strip()

        if not line:
            continue
        if "オストメイト対応トイレ" in line:
            continue
        if "設置市町" in line and "設置場所" in line:
            continue

        lines.append(line)

    anchor_re = re.compile(
        r"^(\d+)\s+(\S+)(?:\s+(.+))?$"
    )

    records = []
    current = None
    between = []

    def finish_current(next_anchor_has_no_facility=False):
        nonlocal current, between

        if current is None:
            between = []
            return []

        parts = between[:]
        between = []

        carry = []

        if next_anchor_has_no_facility:
            while parts and not is_note(parts[-1]):
                carry.insert(0, parts.pop())

        if not current["facility"]:
            facility_parts = []

            while parts and not is_note(parts[0]):
                facility_parts.append(parts.pop(0))

            current["facility"] = " ".join(
                facility_parts
            ).strip()

        notes = []

        for part in parts:
            if notes and part == "予定":
                notes[-1] += "予定"
            else:
                notes.append(part)

        current["note"] = " ".join(notes).strip()

        records.append(current)
        current = None

        return carry

    for line in lines:
        m = anchor_re.match(line)

        if m:
            no = int(m.group(1))
            municipality = m.group(2)
            facility = (m.group(3) or "").strip()

            carry = finish_current(
                next_anchor_has_no_facility=not facility
            )

            if not facility and carry:
                facility = " ".join(carry).strip()

            current = {
                "no": no,
                "municipality": municipality,
                "facility": facility,
                "note": "",
            }

        else:
            if current is not None:
                between.append(line)

    finish_current(False)

    for record in records:
        override = OVERRIDES.get(record["no"])
        if override:
            record.update(override)

    return records


def main():
    records = parse_records()

    numbers = [r["no"] for r in records]

    assert len(records) == 400
    assert numbers == list(range(1, 401))
    assert all(r["facility"] for r in records)

    output_rows = []

    for r in records:
        no = r["no"]
        municipality = clean(r["municipality"])
        facility = clean(r["facility"])
        source_note = clean(r["note"])

        municipality_code = MUNICIPALITIES.get(
            municipality
        )
        if not municipality_code:
            raise ValueError(
                f"unknown municipality at {no}: "
                f"{municipality!r}"
            )

        if no in SPECIAL_OSTOMATE_UNKNOWN:
            ostomate = "unknown"
        else:
            ostomate = "yes"

        attribute_notes = []

        if no == 77:
            attribute_notes.append(
                "ostomate_status=partial; "
                "pouch_washing_device_present; "
                "other_equipment_not_complete"
            )

        elif no in {87, 88, 89, 90}:
            attribute_notes.append(
                "ostomate_status=planned"
            )

        elif no == 347:
            attribute_notes.append(
                "ostomate_status=partial; "
                "dedicated_sink_absent; shower_only"
            )

        out = {
            "prefecture_code": "42",
            "prefecture_name": "長崎県",
            "municipality_code": municipality_code,
            "municipality_name": municipality,
            "ward_name": "",

            "facility_name": facility,
            "formal_name": "",
            "facility_category": "",
            "postal_code": "",
            "address": "",
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
            "adult_bed": "",
            "ostomate": ostomate,
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
            "source_updated_at": "",
            "source_row": str(no),
            "attribute_note": " | ".join(attribute_notes),
            "note": source_note,
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

    print("input rows :", len(records))
    print("output rows:", len(output_rows))
    print("output     :", OUTPUT)


if __name__ == "__main__":
    main()
