#!/usr/bin/env python3

import csv
import re
from collections import Counter
from pathlib import Path

from schema import FIELDS


ROOT = Path(__file__).resolve().parents[3]

INPUT = (
    ROOT
    / "data/raw/44-大分県/barrier-free/barifuri-oita"
    / "toilet-details.csv"
)

MUNICIPALITIES = ROOT / "data/reference/municipalities.csv"

OUTPUT = (
    ROOT
    / "data/normalized/44-大分県/barrier-free"
    / "oita-barifuri-toilet.csv"
)

SOURCE_NAME = "バリアフリー大分 トイレ"
SOURCE_DATASET = "barifuri_oita_toilet"


TOILET_FIELDS = [
    "多目的トイレ個数",
    "ベビーチェア",
    "ベビーベッド",
    "着替え台",
    "ユニバーサルシート",
    "手すり",
    "ウォシュレット",
    "カーテン",
    "暖房",
    "オストメイト",
    "規模",
    "ほじょ犬・音声・点字",
    "緊急通報装置",
]


EMERGENCY_OVERRIDES = {
    # 詳細表セルには寸法値が入っているが、
    # 一覧・詳細ページのSOSボタン表示で存在確認済み。
    "67042": "あり",
    "74710": "あり",
}


def clean(value):
    if value is None:
        return ""

    return " ".join(
        str(value)
        .replace("\u3000", " ")
        .replace("\n", " ")
        .split()
    )


def facility_name(title):
    return clean(title).split(" ｜", 1)[0]


def municipality_name(title):
    title = clean(title)

    m = re.search(r"｜([^｜]+)｜", title)
    if not m:
        raise ValueError(
            f"municipality not found in title: {title!r}"
        )

    return clean(m.group(1))


def load_municipality_codes():
    result = {}

    with MUNICIPALITIES.open(
        encoding="utf-8-sig",
        newline="",
    ) as f:
        for row in csv.DictReader(f):
            if row["prefecture_code"] != "44":
                continue

            result[row["municipality_name"]] = (
                row["municipality_code"]
            )

    return result


def extract_toilet_fields(text):
    text = clean(text)
    values = {}

    for i, label in enumerate(TOILET_FIELDS):
        start = text.find(label)

        if start < 0:
            values[label] = ""
            continue

        start += len(label)

        if i + 1 < len(TOILET_FIELDS):
            next_label = TOILET_FIELDS[i + 1]
            end = text.find(next_label, start)

            if end < 0:
                end = len(text)
        else:
            # 最終項目は「駐車場 駐車場」まで。
            m = re.search(
                r"\s+駐車場\s+駐車場",
                text[start:],
            )

            if m:
                end = start + m.start()
            else:
                end = len(text)

        values[label] = clean(text[start:end])

    return values


def yes_no_presence(value):
    value = clean(value)

    if not value:
        return ""

    if value in {
        "なし",
        "無し",
        "ともになし",
    }:
        return "no"

    if (
        value == "あり"
        or value == "ともにあり"
        or "あり" in value
    ):
        return "yes"

    raise ValueError(
        f"unsupported presence value: {value!r}"
    )


def multipurpose_presence(text):
    value = extract_section_value(
        text,
        "多目的トイレ",
        "オストメイト",
    )

    if not value:
        return ""

    if value in {"なし", "無し"}:
        return "no"

    return "yes"


def washlet_value(value):
    return yes_no_presence(value)


def adult_bed_value(value):
    return yes_no_presence(value)


def baby_chair_value(value):
    return yes_no_presence(value)


def ostomate_value(value):
    return yes_no_presence(value)


def baby_equipment(value):
    """
    サイトの「ベビーベッド」欄には、
    ベビーベッドそのものと「おむつ交換台」が混在する。

    baby_bed:
      明確に「あり」「なし」と記載された場合だけ設定。

    diaper_changing_space:
      「おむつ交換台」と明記された場合に設定。
    """
    value = clean(value)

    if not value:
        return "", ""

    if "おむつ交換台" in value:
        diaper = "yes"

        # 「女性トイレに...」等も施設内には存在する。
        baby_bed = ""
        return baby_bed, diaper

    if value in {"あり"}:
        return "yes", ""

    if value in {"なし", "ともになし"}:
        return "no", ""

    # 「なし：別室にあり」は施設としては存在するが、
    # トイレ内ではない。施設単位フィールドとして yes。
    if "別室にあり" in value:
        return "yes", ""

    raise ValueError(
        f"unsupported baby-bed value: {value!r}"
    )


def emergency_value(detail_id, value):
    value = clean(
        EMERGENCY_OVERRIDES.get(detail_id, value)
    )

    if value in {"あり"}:
        return "button"

    if value in {
        "なし",
        "無し",
        "ともになし",
    }:
        return "none"

    raise ValueError(
        f"{detail_id}: unsupported emergency value: "
        f"{value!r}"
    )


def extract_lat_lon(text):
    text = clean(text)

    matches = re.findall(
        r"\{\s*lat:\s*(-?\d+(?:\.\d+)?)"
        r"\s*,\s*lng:\s*(-?\d+(?:\.\d+)?)\s*\}",
        text,
    )

    if not matches:
        return "", ""

    # ページ自身のGoogle Maps markerを使用。
    lat, lon = matches[0]
    return lat, lon


def extract_section_value(text, label, next_label):
    text = clean(text)

    m = re.search(
        re.escape(label)
        + r"\s+(.*?)\s+"
        + re.escape(next_label),
        text,
    )

    return clean(m.group(1)) if m else ""


def nursing_space_value(text):
    value = extract_section_value(
        text,
        "授乳室",
        "託児サービス",
    )

    if not value:
        return ""

    if value in {"なし", "無し"}:
        return "no"

    return "yes"


def stroller_value(text):
    value = extract_section_value(
        text,
        "ベビーカー貸出",
        "授乳室",
    )

    if not value:
        return ""

    if value in {"なし", "無し"}:
        return "no"

    return "yes"


def entrance_step_value(text):
    value = extract_section_value(
        text,
        "建物出入口段差",
        "建物出入口スロープ",
    )

    if not value:
        return ""

    if value == "無し":
        return "no"

    if value.startswith("なし"):
        return "no"

    # 段差の存在が明示されているものだけ yes。
    if value in {"あり"}:
        return "yes"

    if value.startswith("あり（") or value.startswith("あり("):
        return "yes"

    if "階段" in value:
        return "yes"

    if "段差" in value:
        return "yes"

    if "上り框" in value:
        return "yes"

    if re.search(r"\d+\s*[㎝cmｍm]", value):
        return "yes"

    if "入口にあり" in value:
        return "yes"

    if "入口の一つにあり" in value:
        return "yes"

    if "殆どの窯元にあり" in value:
        return "yes"

    # 砂利、案内画像、チェーン施錠などは
    # 段差の有無を断定しない。
    return ""


def attribute_note(values, text):
    parts = []

    for label in TOILET_FIELDS:
        value = clean(values.get(label))
        if value:
            parts.append(f"{label}={value}")

    nursing = extract_section_value(
        text,
        "授乳室",
        "託児サービス",
    )
    if nursing:
        parts.append(f"授乳室={nursing}")

    stroller = extract_section_value(
        text,
        "ベビーカー貸出",
        "授乳室",
    )
    if stroller:
        parts.append(
            f"ベビーカー貸出={stroller}"
        )

    entrance = extract_section_value(
        text,
        "建物出入口段差",
        "建物出入口スロープ",
    )
    if entrance:
        parts.append(
            f"建物出入口段差={entrance}"
        )

    return "; ".join(parts)


def main():
    municipality_codes = load_municipality_codes()

    with INPUT.open(
        encoding="utf-8",
        newline="",
    ) as f:
        source_rows = list(csv.DictReader(f))

    assert len(source_rows) == 30

    ids = [clean(r["detail_id"]) for r in source_rows]
    assert len(ids) == len(set(ids))

    output_rows = []

    for r in source_rows:
        detail_id = clean(r["detail_id"])
        title = clean(r["facility_name"])
        facility = facility_name(title)
        municipality = municipality_name(title)

        municipality_code = municipality_codes.get(
            municipality
        )

        if not municipality_code:
            raise ValueError(
                f"{detail_id}: unknown municipality "
                f"{municipality!r}"
            )

        raw = clean(r["toilet_detail_raw"])
        values = extract_toilet_fields(raw)

        baby_bed, diaper = baby_equipment(
            values["ベビーベッド"]
        )

        latitude, longitude = extract_lat_lon(raw)

        out = {
            "prefecture_code": "44",
            "prefecture_name": "大分県",
            "municipality_code": municipality_code,
            "municipality_name": municipality,
            "ward_name": "",

            "facility_name": facility,
            "formal_name": "",
            "facility_category": "",
            "postal_code": "",
            "address": clean(r["address"]),
            "latitude": latitude,
            "longitude": longitude,
            "homepage_url": clean(r["detail_url"]),

            "multipurpose_toilet":
                multipurpose_presence(raw),
            "wheelchair_toilet":
                (
                    "yes"
                    if detail_id == "60536"
                    else ""
                ),
            "toilet_floor": "",
            "unisex_toilet_count": "",
            "male_toilet_count": "",
            "female_toilet_count": "",

            "washlet":
                washlet_value(
                    values["ウォシュレット"]
                ),
            "adult_bed":
                adult_bed_value(
                    values["ユニバーサルシート"]
                ),
            "ostomate":
                ostomate_value(
                    values["オストメイト"]
                ),
            "voice_guidance": "",
            "baby_bed": baby_bed,
            "baby_chair":
                baby_chair_value(
                    values["ベビーチェア"]
                ),
            "child_toilet": "",
            "child_chair": "",
            "flush_type": "",
            "emergency_call_type":
                emergency_value(
                    detail_id,
                    values["緊急通報装置"],
                ),

            "male_urinal_with_rail": "",
            "male_western_toilet": "",
            "female_western_toilet": "",
            "male_baby_bed": "",
            "female_baby_bed": "",
            "male_baby_chair": "",
            "female_baby_chair": "",

            "entrance_step":
                entrance_step_value(raw),
            "stroller_rental":
                stroller_value(raw),
            "nursing_space":
                nursing_space_value(raw),
            "diaper_changing_space": diaper,
            "kids_room": "",

            "source_dataset": SOURCE_DATASET,
            "source_name": SOURCE_NAME,
            "source_url": clean(r["detail_url"]),
            "source_updated_at": "",
            "source_row": detail_id,
            "attribute_note":
                attribute_note(values, raw),
            "note": "",
        }

        output_rows.append(out)

    assert len(output_rows) == 30
    assert all(
        len(set(row) - set(FIELDS)) == 0
        for row in output_rows
    )

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

    print("input rows :", len(source_rows))
    print("output rows:", len(output_rows))
    print("columns    :", len(FIELDS))
    print("output     :", OUTPUT)

    for field in (
        "multipurpose_toilet",
        "washlet",
        "adult_bed",
        "ostomate",
        "baby_bed",
        "baby_chair",
        "emergency_call_type",
        "entrance_step",
        "stroller_rental",
        "nursing_space",
        "diaper_changing_space",
    ):
        print()
        print(
            field,
            dict(
                Counter(
                    row[field]
                    for row in output_rows
                )
            ),
        )


if __name__ == "__main__":
    main()
