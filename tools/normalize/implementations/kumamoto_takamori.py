#!/usr/bin/env python3
"""Normalize Kumamoto Data Linkage Platform PublicToilet CSV for Takamori Town.

The source uses the Kumamoto NGSI PublicToilet data model rather than the
repository's 39-column Japanese ODS CSV. Field correspondence follows the
Kumamoto data-model definition. `location` may be a latitude,longitude pair or GeoJSON Point [longitude, latitude].
Source files are never modified.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[2]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from normalize_public_toilet import apply_patches, load_patches
from tools.normalize.core.normalization import (
    LenientHmsTimeStrategy,
    RowSupport,
    StandardCsvWriter,
)

ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = ROOT / "data" / "raw" / "43-熊本県" / "43428-高森町" / "public-toilet"
OUT = ROOT / "data" / "normalized" / "43-熊本県" / "43428-高森町" / "public-toilet" / "public-toilet.csv"
SCHEMA = ROOT / "schema" / "standard" / "public-toilet" / "schema.csv"

SOURCE_TO_STANDARD = {
    "localGovernmentCode": "全国地方公共団体コード",
    "identification": "ID",
    "localGovernmentName": "地方公共団体名",
    "name": "名称",
    "nameKana": "名称_カナ",
    "nameEn": "名称_英語",
    "localGovernmentSubCode": "所在地_全国地方公共団体コード",
    "streetAddressId": "町字ID",
    "fullAddress": "所在地_連結表記",
    "prefecture": "所在地_都道府県",
    "cityAndCounty": "所在地_市区町村",
    "streetAddress": "所在地_町字",
    "cityBlock": "所在地_番地以下",
    "buildingNameEtc": "建物名等(方書)",
    "placeOfInstallation": "設置位置",
    "altitudeType": "高度の種別",
    "altitudeValue": "高度の値",
    "menToiletTotal": "男性トイレ総数",
    "menToiletUrinal": "男性トイレ数（小便器）",
    "menToiletJapanese": "男性トイレ数（和式）",
    "menToiletWestern": "男性トイレ数（洋式）",
    "womenToiletTotal": "女性トイレ総数",
    "womenToiletJapanese": "女性トイレ数（和式）",
    "womenToiletWestern": "女性トイレ数（洋式）",
    "allGenderToiletTotal": "男女共用トイレ総数",
    "allGenderToiletJapanese": "男女共用トイレ数（和式）",
    "allGenderToiletWestern": "男女共用トイレ数（洋式）",
    "multipurposeToilet": "バリアフリートイレ数",
    "wheelchairUserToilet": "車椅子使用者用トイレ有無",
    "toiletForInfants": "乳幼児用設備設置トイレ有無",
    "toiletForOstomates": "オストメイト設置トイレ有無",
    "startTime": "利用開始時間",
    "endTime": "利用終了時間",
    "dateTimeRemarks": "利用可能時間特記事項",
    "picture": "画像",
    "pictureLicense": "画像_ライセンス",
    "remarks": "備考",
}

EXPECTED_SOURCE = {
    "id", "type", *SOURCE_TO_STANDARD.keys(), "location", "uploadDate"
}

_HM = re.compile(r"^(\d{1,2}):(\d{2})$")
_HMS = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2})$")


TIME_NORMALIZER = LenientHmsTimeStrategy(normalize_fullwidth_colon=False)


def read_schema() -> list[str]:
    with SCHEMA.open(encoding="utf-8-sig", newline="") as f:
        return [row["name"] for row in csv.DictReader(f)]


def read_source(path: Path) -> list[dict[str, str]]:
    raw = path.read_bytes()
    text = None
    encoding = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            text = raw.decode(enc)
            encoding = enc
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise RuntimeError(f"CSV encoding could not be detected: {path}")

    reader = csv.reader(text.splitlines())
    header_raw = next(reader, None)
    if not header_raw:
        raise RuntimeError(f"empty CSV: {path}")
    header = [RowSupport.clean(x) for x in header_raw]
    if len(header) != len(set(header)):
        raise RuntimeError(f"duplicate source columns after trimming: {header}")

    missing = sorted(EXPECTED_SOURCE - set(header))
    extra = sorted(set(header) - EXPECTED_SOURCE)
    if missing or extra:
        raise RuntimeError(
            f"unexpected source schema: missing={missing} extra={extra} columns={len(header)}"
        )

    rows: list[dict[str, str]] = []
    for line_no, values in enumerate(reader, 2):
        if not any(RowSupport.clean(v) for v in values):
            continue
        if len(values) != len(header):
            raise RuntimeError(
                f"row {line_no}: expected {len(header)} columns, got {len(values)}"
            )
        rows.append({header[i]: RowSupport.clean(values[i]) for i in range(len(header))})

    print(f"source: {path.name} encoding={encoding} rows={len(rows)} columns={len(header)}")
    return rows


def parse_location(value: str, line_no: int) -> tuple[str, str]:
    value = RowSupport.clean(value)
    if not value:
        return "", ""

    # Takamori currently publishes location as "latitude,longitude".
    # GeoJSON Point is also accepted defensively.
    if "," in value and not value.lstrip().startswith("{"):
        parts = [part.strip() for part in value.split(",")]
        if len(parts) != 2:
            raise RuntimeError(f"row {line_no}: invalid location pair: {value!r}")
        try:
            latitude = float(parts[0])
            longitude = float(parts[1])
        except ValueError as e:
            raise RuntimeError(
                f"row {line_no}: non-numeric location pair: {value!r}"
            ) from e
    else:
        try:
            obj = json.loads(value)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"row {line_no}: location is neither lat,lon nor valid JSON: {value!r}"
            ) from e

        if not isinstance(obj, dict) or obj.get("type") != "Point":
            raise RuntimeError(
                f"row {line_no}: location is not GeoJSON Point: {value!r}"
            )

        coords = obj.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2:
            raise RuntimeError(
                f"row {line_no}: location.coordinates is invalid: {value!r}"
            )

        try:
            longitude = float(coords[0])
            latitude = float(coords[1])
        except (TypeError, ValueError) as e:
            raise RuntimeError(
                f"row {line_no}: non-numeric location: {value!r}"
            ) from e

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise RuntimeError(f"row {line_no}: location out of range: {value!r}")

    return format(latitude, ".15g"), format(longitude, ".15g")



def main() -> int:
    sources = sorted(RAW_DIR.glob("*.csv"))
    if len(sources) != 1:
        raise SystemExit(f"expected exactly one CSV in {RAW_DIR}, found {len(sources)}")

    fields = read_schema()
    if len(fields) != 39:
        raise RuntimeError(f"expected 39 standard columns, got {len(fields)}")

    source_rows = read_source(sources[0])
    output: list[dict[str, str]] = []

    for line_no, row in enumerate(source_rows, 2):
        out = {field: "" for field in fields}
        for source_name, target_name in SOURCE_TO_STANDARD.items():
            out[target_name] = RowSupport.clean(row.get(source_name))

        out["利用開始時間"] = TIME_NORMALIZER(out["利用開始時間"])
        out["利用終了時間"] = TIME_NORMALIZER(out["利用終了時間"])
        latitude, longitude = parse_location(row.get("location", ""), line_no)
        out["緯度"] = latitude
        out["経度"] = longitude

        # Preserve linkage-platform metadata that has no standard 39-column destination.
        RowSupport.append_labeled_note(out, "NGSI_EntityId", row.get("id", ""))
        RowSupport.append_labeled_note(out, "uploadDate", row.get("uploadDate", ""))

        output.append(out)

    patches = load_patches("43-熊本県", "43428-高森町")
    applied, problems = apply_patches(output, patches, sources[0])
    if problems:
        for msg in problems:
            print(f"PATCH ERROR: {msg}", file=sys.stderr)
        raise RuntimeError(f"Patch verification failed for {sources[0]}")

    if OUT.exists():
        raise SystemExit(f"refusing to overwrite existing normalized file: {OUT}")
    StandardCsvWriter().write(OUT, fields, output)
    print(f"normalized: {len(output)} rows patches={applied} -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
