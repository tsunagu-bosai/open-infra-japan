#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

from tools.normalize.core.schema import read_schema_fields
from tools.normalize.core.normalization import RowSupport
from tools.normalize.core.municipality import six_digit_municipality_code


ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "schema/standard/public-toilet/schema.csv"

EXPECTED_HEADER = [
    "都道府県コード又は市区町村コード",
    "NO",
    "都道府県名又は市町村名",
    "名称",
    "名称_カナ",
    "住所",
    "設置位置",
    "緯度",
    "経度",
    "備考",
]

TARGETS = {
    "06201-山形市",
    "06202-米沢市",
    "06203-鶴岡市",
    "06204-酒田市",
    "06205-新庄市",
    "06206-寒河江市",
    "06207-上山市",
    "06208-村山市",
    "06209-長井市",
    "06211-東根市",
    "06212-尾花沢市",
    "06213-南陽市",
    "06302-中山町",
    "06321-河北町",
    "06322-西川町",
    "06323-朝日町",
    "06324-大江町",
    "06362-最上町",
    "06365-大蔵村",
    "06402-白鷹町",
    "06461-遊佐町",
}



def normalize_target(target: str, fields: list[str]) -> tuple[Path, int]:
    code5, municipality_name = target.split("-", 1)
    source = (
        ROOT
        / "data/raw/06-山形県"
        / target
        / "public-toilet/public_toilet.csv"
    )
    output = (
        ROOT
        / "data/normalized/06-山形県"
        / target
        / "public-toilet/public-toilet.csv"
    )

    with source.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != EXPECTED_HEADER:
            raise RuntimeError(
                f"unexpected header: {source}: {reader.fieldnames!r}"
            )
        source_rows = list(reader)

    rows: list[dict[str, str]] = []

    for source_row in source_rows:
        if not any(RowSupport.clean(value) for value in source_row.values()):
            continue

        row = {field: "" for field in fields}

        raw_code = RowSupport.clean(
            source_row.get("都道府県コード又は市区町村コード")
        )
        raw_code6 = raw_code.zfill(6) if raw_code else ""
        if (
            len(raw_code6) != 6
            or not raw_code6.isdigit()
            or raw_code6[:5] != code5
        ):
            raise RuntimeError(
                f"municipality code mismatch: {target}: "
                f"raw={raw_code!r} normalized={raw_code6!r} "
                f"expected-prefix={code5!r}"
            )

        code6 = six_digit_municipality_code(code5)

        source_name = RowSupport.clean(source_row.get("都道府県名又は市町村名"))
        if source_name != municipality_name:
            raise RuntimeError(
                f"municipality name mismatch: {target}: "
                f"raw={source_name!r}"
            )

        row["全国地方公共団体コード"] = code6
        row["ID"] = RowSupport.clean(source_row.get("NO"))
        row["地方公共団体名"] = municipality_name
        row["名称"] = RowSupport.clean(source_row.get("名称"))
        row["名称_カナ"] = RowSupport.clean(source_row.get("名称_カナ"))
        row["所在地_連結表記"] = RowSupport.clean(source_row.get("住所"))
        row["所在地_都道府県"] = "山形県"
        row["所在地_市区町村"] = municipality_name
        row["設置位置"] = RowSupport.clean(source_row.get("設置位置"))
        row["緯度"] = RowSupport.clean(source_row.get("緯度"))
        row["経度"] = RowSupport.clean(source_row.get("経度"))
        row["備考"] = RowSupport.clean(source_row.get("備考"))

        rows.append(row)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    return output, len(rows)


def main() -> None:
    fields = read_schema_fields(SCHEMA)

    for target in sorted(TARGETS):
        output, count = normalize_target(target, fields)
        print(
            f"{target} -> {output.relative_to(ROOT)}: "
            f"{count} rows type=yamagata_simple10 encoding=utf-8-sig"
        )


if __name__ == "__main__":
    main()
