#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from tools.normalize.core.normalization import RowSupport
from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.xlsx import read_xlsx_values


ROOT = Path.cwd()
RAW = ROOT / "data/raw/12-千葉県/12221-八千代市/public-toilet"
OUT = ROOT / "data/normalized/12-千葉県/12221-八千代市/public-toilet/public-toilet.csv"
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {"12221-八千代市"}

CODE6 = "122211"
MUNICIPALITY = "八千代市"
PREFECTURE = "千葉県"



def note(parts: list[str]) -> str:
    return " / ".join(part for part in parts if part)


def base_row(schema: list[str]) -> dict[str, str]:
    row = {field: "" for field in schema}
    row["全国地方公共団体コード"] = CODE6
    row["所在地_全国地方公共団体コード"] = CODE6
    row["地方公共団体名"] = MUNICIPALITY
    row["所在地_都道府県"] = PREFECTURE
    row["所在地_市区町村"] = MUNICIPALITY
    return row


def parse_park(schema: list[str]) -> list[dict[str, str]]:
    rows = read_xlsx_values(RAW / "park.xlsx")
    out: list[dict[str, str]] = []

    for physical_row, values in enumerate(rows, 1):
        values = [RowSupport.clean(v) for v in values]
        if len(values) < 7:
            values += [""] * (7 - len(values))

        number = values[0]
        name = values[1]
        if not number.isdigit() or not name:
            continue

        row = base_row(schema)
        row["ID"] = f"12221-PARK-{number}"
        row["名称"] = name
        row["設置位置"] = values[2]

        notes = [
            f"原データ番号={number}",
            f"原データ構造={values[3]}" if values[3] else "",
            f"原データ方式={values[4]}" if values[4] else "",
            f"原データ大便器={values[5]}" if values[5] else "",
            f"原データ小便器={values[6]}" if values[6] else "",
        ]
        row["備考"] = note(notes)
        out.append(row)

    if not out:
        raise RuntimeError("park source produced no facility rows")

    return out


def station_id(name: str, address: str, lat: str, lon: str) -> str:
    material = f"12221|station|{name}|{address}|{lat}|{lon}".encode("utf-8")
    digest = hashlib.sha256(material).hexdigest()[:12].upper()
    return f"12221-STATION-{digest}"


def parse_station(schema: list[str]) -> list[dict[str, str]]:
    rows = read_xlsx_values(RAW / "station.xlsx")
    out: list[dict[str, str]] = []
    current: dict[str, str] | None = None

    for physical_row, values in enumerate(rows, 1):
        values = [RowSupport.clean(v) for v in values]
        if len(values) < 7:
            values += [""] * (7 - len(values))

        name = values[1]
        address = values[2]
        lot = values[3]
        phone = values[4]
        lat = values[5]
        lon = values[6]

        # ヘッダー行を除外する。
        if name == "施設名":
            continue

        # 住所・座標を持つ行は実施設行。
        if name and address and lat and lon:
            row = base_row(schema)
            row["ID"] = station_id(name, address, lat, lon)
            row["名称"] = name
            row["所在地_連結表記"] = address
            row["緯度"] = lat
            row["経度"] = lon

            notes = [
                f"原データ所在地（地番）={lot}" if lot else "",
                f"原データ電話番号={phone}" if phone and phone != "-" else "",
            ]
            row["備考"] = note(notes)
            out.append(row)
            current = row
            continue

        # 実施設行の後に続く「内訳」行は、その施設の原データ情報として保持する。
        # 「身体障害者対応トイレ」は「車椅子使用者用トイレ」と完全同義とは
        # 断定せず、設備フラグには推測変換しない。
        if current is not None and name and name != "（内訳）":
            current["備考"] = note(
                [current["備考"], f"原データ内訳={name}"]
            )

    if not out:
        raise RuntimeError("station source produced no facility rows")

    return out


def parse_tourism(schema: list[str]) -> list[dict[str, str]]:
    rows = read_xlsx_values(RAW / "tourism.xlsx")
    out: list[dict[str, str]] = []

    for physical_row, values in enumerate(rows, 1):
        values = [RowSupport.clean(v) for v in values]
        if len(values) < 6:
            values += [""] * (6 - len(values))

        number, name, address, phone, lat, lon = values[:6]
        if not number.isdigit() or not name:
            continue

        row = base_row(schema)
        row["ID"] = f"12221-TOURISM-{number}"
        row["名称"] = name
        row["所在地_連結表記"] = address
        row["緯度"] = lat
        row["経度"] = lon

        notes = [
            f"原データNo.={number}",
            f"原データ電話番号={phone}" if phone else "",
        ]
        row["備考"] = note(notes)
        out.append(row)

    if not out:
        raise RuntimeError("tourism source produced no facility rows")

    return out


def main() -> None:
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    if OUT.exists():
        raise RuntimeError(f"normalized already exists: {OUT}")

    park_rows = parse_park(schema)
    station_rows = parse_station(schema)
    tourism_rows = parse_tourism(schema)
    rows = [*park_rows, *station_rows, *tourism_rows]

    ids = [row["ID"] for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate IDs")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=schema, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(
        "12221-八千代市 "
        f"park={len(park_rows)} station={len(station_rows)} "
        f"tourism={len(tourism_rows)} total={len(rows)}"
    )


if __name__ == "__main__":
    main()
