#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from pathlib import Path

from tools.normalize.core.normalization import (
    RowSupport,
    StandardCsvWriter,
    StrictEndOfDayTimeStrategy,
    ValueCleaner,
)

ROOT = Path.cwd()
RAW_ROOT = ROOT / "data/raw"
NORMALIZED_ROOT = ROOT / "data/normalized"
SCHEMA = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "37201": {
        "pref_dir": "37-香川県",
        "mun_dir": "37201-高松市",
        "localgov_code": "372013",
    },
}

EXPECTED_HEADER = [
    "#property", "latitude", "longitude", "prefCode", "identification",
    "pref", "city", "name", "fullNameInKana", "fullNameInRomaji",
    "address", "katagaki", "installationPosition", "totalMensRestroom",
    "smallMensRestroom", "japaneseMensRestroom", "westernMensRestroom",
    "totalWomanRestroom", "japaneseWomanRestroom", "westernWomanRestroom",
    "sharedRestroom", "japaneseSharedRestroom", "westernSharedRestroom",
    "multifunctionalRestroom", "wheelchairRestroom", "anInfantRestroom",
    "ostomateRestroom", "startTime", "endTime", "availableDateNote",
    "image", "iamgeLicense", "note",
]

DIRECT = {
    "identification": "ID",
    "name": "名称",
    "fullNameInKana": "名称_カナ",
    "fullNameInRomaji": "名称_英語",
    "address": "所在地_連結表記",
    "pref": "所在地_都道府県",
    "city": "所在地_市区町村",
    "katagaki": "建物名等(方書)",
    "installationPosition": "設置位置",
    "latitude": "緯度",
    "longitude": "経度",
    "totalMensRestroom": "男性トイレ総数",
    "smallMensRestroom": "男性トイレ数（小便器）",
    "japaneseMensRestroom": "男性トイレ数（和式）",
    "westernMensRestroom": "男性トイレ数（洋式）",
    "totalWomanRestroom": "女性トイレ総数",
    "japaneseWomanRestroom": "女性トイレ数（和式）",
    "westernWomanRestroom": "女性トイレ数（洋式）",
    "sharedRestroom": "男女共用トイレ総数",
    "japaneseSharedRestroom": "男女共用トイレ数（和式）",
    "westernSharedRestroom": "男女共用トイレ数（洋式）",
    "wheelchairRestroom": "車椅子使用者用トイレ有無",
    "anInfantRestroom": "乳幼児用設備設置トイレ有無",
    "ostomateRestroom": "オストメイト設置トイレ有無",
    "image": "画像",
    "iamgeLicense": "画像_ライセンス",
    "note": "備考",
}

COUNT_SOURCE_FIELDS = (
    "totalMensRestroom", "smallMensRestroom", "japaneseMensRestroom",
    "westernMensRestroom", "totalWomanRestroom", "japaneseWomanRestroom",
    "westernWomanRestroom", "sharedRestroom", "japaneseSharedRestroom",
    "westernSharedRestroom", "multifunctionalRestroom",
)


def read_schema() -> list[str]:
    with SCHEMA.open("r", encoding="utf-8-sig", newline="") as f:
        return [r["name"] for r in csv.DictReader(f)]



CLEAN_OPTIONAL = ValueCleaner({"ー", "－", "-"})


TIME_NORMALIZER = StrictEndOfDayTimeStrategy(cleaner=CLEAN_OPTIONAL)



def main() -> int:
    schema = read_schema()
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    for code, cfg in TARGETS.items():
        raw_dir = RAW_ROOT / cfg["pref_dir"] / cfg["mun_dir"] / "public-toilet"
        sources = sorted(raw_dir.glob("*.csv"))
        if len(sources) != 1:
            raise RuntimeError(
                f"{code}: expected exactly one raw CSV, got "
                + ", ".join(p.name for p in sources)
            )

        with sources[0].open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if (reader.fieldnames or []) != EXPECTED_HEADER:
                raise RuntimeError(
                    f"{code}: unexpected source header: {reader.fieldnames!r}"
                )
            source_rows = [
                {k: CLEAN_OPTIONAL(v or "") for k, v in row.items()}
                for row in reader
                if any(CLEAN_OPTIONAL(v or "") for v in row.values())
            ]

        normalized: list[dict[str, str]] = []
        multifunctional_preserved = 0
        end_24_corrected = 0

        for source in source_rows:
            if source["prefCode"] != code:
                raise RuntimeError(
                    f"{code}: unexpected prefCode={source['prefCode']!r}"
                )
            if source["pref"] != "香川県" or source["city"] != "高松市":
                raise RuntimeError(
                    f"{code}: unexpected municipality "
                    f"pref={source['pref']!r} city={source['city']!r}"
                )
            if source["#property"] != source["identification"]:
                raise RuntimeError(
                    f"{code}: #property and identification differ: "
                    f"{source['#property']!r} != {source['identification']!r}"
                )

            for field in COUNT_SOURCE_FIELDS:
                value = source[field]
                if value and not value.isdigit():
                    raise RuntimeError(
                        f"{code}: unexpected count {field}={value!r} "
                        f"ID={source['identification']!r}"
                    )

            row = {k: "" for k in schema}
            row["全国地方公共団体コード"] = cfg["localgov_code"]
            row["地方公共団体名"] = "高松市"
            row["所在地_全国地方公共団体コード"] = cfg["localgov_code"]

            for source_field, target_field in DIRECT.items():
                row[target_field] = source[source_field]

            for field in (
                "車椅子使用者用トイレ有無",
                "乳幼児用設備設置トイレ有無",
                "オストメイト設置トイレ有無",
            ):
                if row[field] not in {"", "有", "無"}:
                    raise RuntimeError(
                        f"{code}: unexpected boolean {field}={row[field]!r}"
                    )

            multifunctional = source["multifunctionalRestroom"]
            if multifunctional:
                RowSupport.append_note(row, f"原データmultifunctionalRestroom={multifunctional}")
                multifunctional_preserved += 1

            row["利用開始時間"] = TIME_NORMALIZER(
                source["startTime"], row, "startTime"
            )
            row["利用終了時間"] = TIME_NORMALIZER(
                source["endTime"], row, "endTime"
            )
            if source["endTime"] == "24:00":
                end_24_corrected += 1

            row["利用可能時間特記事項"] = source["availableDateNote"]
            normalized.append(row)

        ids = [row["ID"] for row in normalized]
        if not ids or any(not value for value in ids) or len(ids) != len(set(ids)):
            raise RuntimeError(f"{code}: identification must be populated and unique")

        out = (
            NORMALIZED_ROOT
            / cfg["pref_dir"]
            / cfg["mun_dir"]
            / "public-toilet/public-toilet.csv"
        )
        StandardCsvWriter().write(out, schema, normalized)

        print(
            f"{code} {cfg['mun_dir']}: rows={len(normalized)} "
            f"source={sources[0].name} "
            f"multifunctional_preserved={multifunctional_preserved} "
            f"end_24_corrected={end_24_corrected}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
