#!/usr/bin/env python3
"""Validate the self-contained refill publication files in ``dist/``."""
from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

FREE_FIELDS = [
    "source_id", "facility_name", "address", "latitude", "longitude",
    "source_url", "service_type", "seasonal", "season_note",
]
DISCOUNT_FIELDS = [
    "discount_id", "candidate_id", "facility_name", "address", "latitude",
    "longitude", "source_url", "service_type", "discount_content",
]
ATTRIBUTION_FIELDS = [
    "source_id", "facility_name", "service_info_url", "coordinate_source_reference",
    "coordinate_source_name", "coordinate_license", "coordinate_license_url",
    "record_source_names", "record_source_urls", "record_licenses",
    "record_license_urls", "record_attributions",
]
DISCOUNT_ATTRIBUTION_FIELDS = [
    "discount_id", "candidate_id", "facility_name", "coordinate_source_reference",
    "coordinate_source_name", "coordinate_attribution",
]
AUDIT_FIELDS = {
    "audit_reason", "evidence_text", "evidence_reference", "review_status",
    "review_history", "candidate_latitude", "candidate_longitude", "notes",
    "decision_source_column", "service_evidence_text",
}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        raise ValueError(f"required publication file is missing: {path.relative_to(ROOT)}")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError(f"CSV header is missing: {path.relative_to(ROOT)}")
        return reader.fieldnames, list(reader)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(year: int) -> list[str]:
    errors: list[str] = []
    try:
        free_header, free = read_csv(DIST / "refill-water-spots.csv")
        discount_header, discount = read_csv(DIST / "refill-discount-services.csv")
        attribution_header, attribution = read_csv(DIST / "refill-publication-attribution.csv")
        discount_attribution_header, discount_attribution = read_csv(DIST / "refill-discount-coordinate-attribution.csv")
        attribution_md_path = DIST / "ATTRIBUTION.md"
        require(attribution_md_path.is_file(), "required publication file is missing: dist/ATTRIBUTION.md")
        require(not (DIST / "refill-water-spots-free.csv").exists(), "obsolete filename remains: dist/refill-water-spots-free.csv")
        attribution_md = attribution_md_path.read_text(encoding="utf-8")
        require("refill-discount-coordinate-attribution.csv" in attribution_md and "国土地理院" in attribution_md,
                "ATTRIBUTION.md must document discount coordinate provenance and the prior GSI review")
        for required in (
            "Geolonia Japanese Addresses v2",
            "@geolonia/normalize-japanese-addresses 3.1.3",
            "https://creativecommons.org/licenses/by/4.0/deed.ja",
            "代表座標を補完",
            "© OpenStreetMap contributors",
            "https://opendatacommons.org/licenses/odbl/1-0/",
            "https://www.openstreetmap.org/copyright",
            "msearch.gsi.go.jp/address-search/AddressSearch",
            "未確認",
        ):
            require(required in attribution_md, f"ATTRIBUTION.md is missing required source/license disclosure: {required}")

        require(free_header == FREE_FIELDS, f"free CSV columns differ from schema: {free_header}")
        require(discount_header == DISCOUNT_FIELDS, f"discount CSV columns differ from schema: {discount_header}")
        require(attribution_header == ATTRIBUTION_FIELDS, f"attribution CSV columns differ from schema: {attribution_header}")
        require(discount_attribution_header == DISCOUNT_ATTRIBUTION_FIELDS, f"discount attribution CSV columns differ from schema: {discount_attribution_header}")
        require(not (AUDIT_FIELDS & set(free_header + discount_header + attribution_header + discount_attribution_header)), "internal audit columns found in a public CSV")

        require(len(free) == 4093, f"expected 4093 refill rows, found {len(free)}")
        require(len(discount) == 16, f"expected 16 discount rows, found {len(discount)}")
        require(len(discount_attribution) == 16, f"expected 16 discount coordinate attribution rows, found {len(discount_attribution)}")
        free_ids = [row["source_id"].strip() for row in free]
        discount_ids = [row["discount_id"].strip() for row in discount]
        candidate_ids = [row["candidate_id"].strip() for row in discount]
        require(len(free_ids) == len(set(free_ids)) and all(free_ids), "refill source_id values are blank or duplicated")
        require(len(discount_ids) == len(set(discount_ids)) and all(discount_ids), "discount_id values are blank or duplicated")
        require(len(candidate_ids) == len(set(candidate_ids)) and all(candidate_ids), "candidate_id values are blank or duplicated")

        required_free = [field for field in FREE_FIELDS if field != "season_note"]
        required_discount = DISCOUNT_FIELDS
        for label, rows, fields in (("refill", free, required_free), ("discount", discount, required_discount)):
            for row in rows:
                missing = [field for field in fields if not row.get(field, "").strip()]
                require(not missing, f"{label} row {row.get('source_id') or row.get('discount_id')} has blank fields: {missing}")
                lat, lon = float(row["latitude"]), float(row["longitude"])
                require(math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180,
                        f"{label} row {row.get('source_id') or row.get('discount_id')} has out-of-range coordinates")

        require(all(row["service_type"] in {"free_refill", "unknown"} for row in free), "refill CSV contains an invalid service_type")
        require(sum(row["service_type"] == "free_refill" for row in free) == 813, "free_refill count differs from the 2026 publication baseline (813)")
        require(sum(row["service_type"] == "unknown" for row in free) == 3280, "unknown count differs from the 2026 publication baseline (3280)")
        require(all(row["service_type"] in {"discount", "both"} for row in discount), "discount CSV contains an invalid service_type")
        require(sum(row["service_type"] == "discount" for row in discount) == 15 and sum(row["service_type"] == "both" for row in discount) == 1,
                "discount service counts must be 15 discount and 1 both")
        discount_by_id = {row["discount_id"].strip(): row for row in discount}
        require(len(discount_by_id) == 16, "discount_id values are duplicated")
        discount_attr_ids = [row["discount_id"].strip() for row in discount_attribution]
        require(len(discount_attr_ids) == len(set(discount_attr_ids)), "discount coordinate attribution IDs are duplicated")
        require(set(discount_attr_ids) == set(discount_by_id), "discount coordinate attribution discount_id set differs from discount CSV")
        discount_by_candidate = {row["candidate_id"].strip(): row for row in discount}
        require(sum("openstreetmap.org/" in row["coordinate_source_reference"] for row in discount_attribution) == 5,
                "five reviewed discount coordinate rows must use OSM venue-area coordinates")
        require(sum("japanese-addresses-v2.geoloniamaps.com/api/ja/" in row["coordinate_source_reference"] for row in discount_attribution) == 11,
                "eleven discount coordinate rows must use Geolonia address data")
        require(not any("msearch.gsi.go.jp/address-search/AddressSearch" in row["coordinate_source_reference"] for row in discount_attribution),
                "unresolved GSI address-search coordinates must not remain in discount CSV")
        for row in discount_attribution:
            for field in DISCOUNT_ATTRIBUTION_FIELDS:
                require(bool(row.get(field, "").strip()), f"discount coordinate attribution has blank {field}: {row.get('candidate_id')}")
            candidate_id = row["candidate_id"].strip()
            require(candidate_id in discount_by_candidate, f"unknown discount candidate_id in coordinate attribution: {candidate_id}")
            require(row["discount_id"].strip() == discount_by_candidate[candidate_id]["discount_id"].strip(), f"discount coordinate attribution ID mismatch: {candidate_id}")
            require(row["facility_name"].strip() == discount_by_candidate[candidate_id]["facility_name"].strip(), f"discount coordinate attribution facility mismatch: {candidate_id}")
            ref = row["coordinate_source_reference"]
            name = row["coordinate_source_name"]
            if "japanese-addresses-v2.geoloniamaps.com/api/ja/" in ref:
                require("Geolonia" in name, f"discount Geolonia coordinate source name is missing: {candidate_id}")
                require("https://creativecommons.org/licenses/by/4.0/deed.ja" in row["coordinate_attribution"],
                        f"discount Geolonia CC BY 4.0 attribution is missing: {candidate_id}")
            elif "openstreetmap.org/" in ref:
                require("OpenStreetMap" in name, f"discount OSM coordinate source name is missing: {candidate_id}")
                require("ODbL" in row["coordinate_attribution"] and "openstreetmap.org/copyright" in row["coordinate_attribution"],
                        f"discount OSM attribution/license is missing: {candidate_id}")
            else:
                require("msearch.gsi.go.jp/address-search/AddressSearch" in ref, f"discount coordinate reference is not Geolonia, OSM, or GSI: {candidate_id}")
                require("国土地理院" in name, f"discount coordinate source name is missing GSI: {candidate_id}")
                require("未確認" in row["coordinate_attribution"], f"unresolved GSI terms are not disclosed: {candidate_id}")

        require(all(row["seasonal"] in {"true", "false", "unknown"} for row in free), "free CSV contains an invalid seasonal value")
        require(all((row["seasonal"] == "true") == bool(row["season_note"].strip()) for row in free), "season_note must be populated only when seasonal=true")
        seasonal_count = sum(row["seasonal"] == "true" for row in free)
        require(year != 2026 or seasonal_count == 84, f"expected 84 seasonal rows for 2026, found {seasonal_count}")

        attribution_ids = [row["source_id"].strip() for row in attribution]
        require(len(attribution) == len(free), f"attribution row count differs from free CSV: {len(attribution)} vs {len(free)}")
        require(len(attribution_ids) == len(set(attribution_ids)), "attribution source_id values are duplicated")
        require(set(attribution_ids) == set(free_ids), "attribution source_id set differs from free CSV")
        free_by_id = {row["source_id"].strip(): row for row in free}
        for row in attribution:
            sid = row["source_id"].strip()
            require(bool(row["coordinate_source_reference"].strip()), f"coordinate source reference is blank: {sid}")
            require(row["service_info_url"].strip() == free_by_id[sid]["source_url"].strip(), f"service URL mismatch between attribution and free CSV: {sid}")
            source = (row["coordinate_source_name"] + " " + row["coordinate_source_reference"]).lower()
            if "openstreetmap" in source:
                require("odbl" in row["coordinate_license"].lower() and "openstreetmap.org/copyright" in row["coordinate_license_url"],
                        f"OSM attribution/license is incomplete: {sid}")
            if "geolonia" in source:
                require("cc by 4.0" in row["coordinate_license"].lower() and row["coordinate_license_url"] == "https://creativecommons.org/licenses/by/4.0/deed.ja",
                        f"Geolonia attribution/license is incomplete: {sid}")
    except (OSError, ValueError, KeyError, csv.Error) as exc:
        errors.append(str(exc))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of-year", type=int, default=2026, help="publication edition year (default: 2026)")
    args = parser.parse_args()
    errors = validate(args.as_of_year)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OK: refill publication files validated for {args.as_of_year}")
    print("water=4093, discount=16, discount_coordinate_attribution=16, seasonal=true=" + str(args.as_of_year == 2026 and 84 or "not edition-locked"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
