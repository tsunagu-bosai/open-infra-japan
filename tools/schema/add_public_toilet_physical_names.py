#!/usr/bin/env python3
from __future__ import annotations
import csv
from pathlib import Path

SCHEMA = Path("schema/standard/public-toilet/schema.csv")
PHYSICAL = ['localgov_code', 'id', 'localgov_name', 'name', 'name_kana', 'name_english', 'seat_localgov_code', 'choaza_id', 'seat_copulative_spell', 'seat_prefecture', 'seat_city', 'seat_choaza', 'seat_after_address', 'buillding_name_etc', 'set_position', 'latitude', 'longitude', 'advanced_classification', 'advanced_value', 'male_wc_total', 'male_wc_urinal', 'male_wc_jstyle', 'male_wc_wstyle', 'female_wc_total', 'female_wc_jstyle', 'female_wc_wstyle', 'unisex_wc_total', 'unisex_wc_jstyle', 'unisex_wc_wstyle', 'barrier_free_wc', 'wheelchair_wc', 'infant_wc', 'ostomate_wc', 'available_start_time', 'available_end_time', 'available_time_note', 'image', 'image_licence', 'note']

def main():
    with SCHEMA.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    if len(rows) != len(PHYSICAL):
        raise RuntimeError(f"Expected {len(PHYSICAL)} schema rows, got {len(rows)}")
    if "physical_name" not in fields:
        fields.append("physical_name")
    for row, physical in zip(rows, PHYSICAL):
        row["physical_name"] = physical
    with SCHEMA.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader(); w.writerows(rows)
    print("Schema rows:", len(rows))
    print("Physical names:", len(PHYSICAL))
    print("Wrote:", SCHEMA)

if __name__ == "__main__":
    main()
