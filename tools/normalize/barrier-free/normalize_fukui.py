#!/usr/bin/env python3

import csv
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

from schema import FIELDS

ROOT = Path(__file__).resolve().parents[3]

INPUT = (
    ROOT
    / "data/raw/18-福井県/barrier-free"
    / "fukui-ostomate.html"
)

OUTPUT = (
    ROOT
    / "data/normalized/18-福井県/barrier-free"
    / "fukui-ostomate.csv"
)

SOURCE_NAME = "福井県 オストメイト対応トイレ設置施設一覧"
SOURCE_URL = "https://www.pref.fukui.lg.jp/doc/shougai/fmatijourei/osutomeito.html"
SOURCE_UPDATED_AT = "2024-08-01"

MUNICIPALITY_CODES = {
    "福井市": "18201",
    "敦賀市": "18202",
    "小浜市": "18204",
    "大野市": "18205",
    "勝山市": "18206",
    "鯖江市": "18207",
    "あわら市": "18208",
    "越前市": "18209",
    "坂井市": "18210",
    "永平寺町": "18322",
    "池田町": "18382",
    "南越前町": "18404",
    "越前町": "18423",
    "美浜町": "18442",
    "高浜町": "18481",
    "おおい町": "18483",
    "若狭町": "18501",
}

FACILITY_MUNICIPALITY_OVERRIDES = {
    "杉津PA": ("18202", "敦賀市"),
    "刀根PA": ("18202", "敦賀市"),
    "北鯖江PA": ("18207", "鯖江市"),
    "女形谷PA": ("18210", "坂井市"),
    "南条SA": ("18404", "南越前町"),
}


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.current_table = None
        self.current_row = None
        self.current_cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.current_table = []
        elif tag == "tr" and self.current_table is not None:
            self.current_row = []
        elif tag in ("th", "td") and self.current_row is not None:
            self.current_cell = []

    def handle_data(self, data):
        if self.current_cell is not None:
            self.current_cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("th", "td") and self.current_cell is not None:
            text = " ".join("".join(self.current_cell).split())
            self.current_row.append(text)
            self.current_cell = None

        elif tag == "tr" and self.current_row is not None:
            if self.current_row:
                self.current_table.append(self.current_row)
            self.current_row = None

        elif tag == "table" and self.current_table is not None:
            self.tables.append(self.current_table)
            self.current_table = None


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def warm_water_state(value):
    value = clean(value)

    if value == "○":
        return "yes"
    if value in ("－", "-"):
        return "no"
    if not value:
        return ""

    raise ValueError(f"unexpected warm-water value: {value!r}")


def municipality_from_row(facility_name, address):
    address = clean(address)
    facility_name = clean(facility_name)

    normalized_address = unicodedata.normalize("NFKC", address)
    normalized_facility = unicodedata.normalize("NFKC", facility_name)

    for name, code in MUNICIPALITY_CODES.items():
        if name in normalized_address:
            return code, name

    for key, result in FACILITY_MUNICIPALITY_OVERRIDES.items():
        if key in normalized_facility:
            return result

    raise ValueError(
        f"municipality not found: facility={facility_name!r}, address={address!r}"
    )


def main():
    html = INPUT.read_text(encoding="utf-8", errors="replace")

    parser = TableParser()
    parser.feed(html)

    if not parser.tables:
        raise ValueError("table not found")

    table = parser.tables[0]

    # 1行目はヘッダ
    source_rows = table[1:]

    output_rows = []

    for source_row, row in enumerate(source_rows, start=2):
        if len(row) < 6:
            raise ValueError(
                f"unexpected column count at row {source_row}: {len(row)}"
            )

        facility_name = clean(row[0])
        installation_count = clean(row[1])
        warm_water_raw = clean(row[2])
        source_note = clean(row[3])
        address = clean(row[4])
        phone = clean(row[5])

        if not facility_name:
            continue

        municipality_code, municipality_name = municipality_from_row(
            facility_name,
            address,
        )

        attribute_notes = []

        if installation_count:
            attribute_notes.append(
                f"installation_count={installation_count}"
            )

        if warm_water_raw:
            attribute_notes.append(
                f"warm_water={warm_water_raw}"
            )

        notes = []

        if phone:
            notes.append(f"phone={phone}")

        if source_note:
            notes.append(source_note)

        out = {
            "prefecture_code": "18",
            "prefecture_name": "福井県",
            "municipality_code": municipality_code,
            "municipality_name": municipality_name,
            "ward_name": "",

            "facility_name": facility_name,
            "formal_name": "",
            "facility_category": "",
            "postal_code": "",
            "address": address,
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

            "source_dataset": "ostomate_list",
            "source_name": SOURCE_NAME,
            "source_url": SOURCE_URL,
            "source_updated_at": SOURCE_UPDATED_AT,
            "source_row": str(source_row),
            "attribute_note": " | ".join(attribute_notes),
            "note": " | ".join(notes),
        }

        # 温水対応は共通列がないため attribute_note に原文保持。
        # 値域チェックだけ行う。
        warm_water_state(warm_water_raw)

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
