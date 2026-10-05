#!/usr/bin/env python3

import csv
import re
from html import unescape
from pathlib import Path

from schema import FIELDS

ROOT = Path(__file__).resolve().parents[3]

INPUT_DIR = (
    ROOT
    / "data/raw/45-宮崎県/barrier-free"
    / "miyazaki-accessibility-map/details"
)

URLS = (
    ROOT
    / "data/raw/45-宮崎県/barrier-free"
    / "miyazaki-accessibility-map/urls.txt"
)

OUTPUT = (
    ROOT
    / "data/normalized/45-宮崎県/barrier-free"
    / "miyazaki-accessibility-map.csv"
)

SOURCE_DATASET = "multipurpose_toilet"
SOURCE_NAME = "みやざきアクセシビリティ情報マップ"

MUNICIPALITIES = {
    "宮崎市": "45201",
    "都城市": "45202",
    "延岡市": "45203",
    "日南市": "45204",
    "小林市": "45205",
    "日向市": "45206",
    "串間市": "45207",
    "西都市": "45208",
    "えびの市": "45209",
    "三股町": "45341",
    "高原町": "45361",
    "国富町": "45382",
    "綾町": "45383",
    "高鍋町": "45401",
    "新富町": "45402",
    "西米良村": "45403",
    "木城町": "45404",
    "川南町": "45405",
    "都農町": "45406",
    "門川町": "45421",
    "諸塚村": "45429",
    "椎葉村": "45430",
    "美郷町": "45431",
    "高千穂町": "45441",
    "日之影町": "45442",
    "五ヶ瀬町": "45443",
}


def clean(value):
    if value is None:
        return ""

    value = re.sub(
        r"<br\s*/?>",
        " / ",
        str(value),
        flags=re.I,
    )
    value = re.sub(r"<[^>]+>", " ", value)

    return " ".join(
        unescape(value).split()
    )


def first(pattern, text):
    m = re.search(
        pattern,
        text,
        re.S,
    )

    if not m:
        return ""

    return clean(m.group(1))


def extract_toilet_segment(html):
    label = re.search(
        r'<label\b[^>]*data-tab_code="[^"]+"[^>]*>'
        r'\s*トイレ\s*</label>',
        html,
        re.S,
    )

    if not label:
        raise ValueError("toilet tab not found")

    body = re.search(
        r'<div\b[^>]*class="[^"]*'
        r'p-details__tab__item[^"]*"[^>]*>',
        html[label.end():],
        re.S,
    )

    if not body:
        raise ValueError("toilet body not found")

    start = label.end() + body.end()

    next_tab = re.search(
        r'<input\b[^>]*name="switch__tab01"[^>]*>',
        html[start:],
        re.S,
    )

    if next_tab:
        return html[
            start:start + next_tab.start()
        ]

    return html[start:]


def extract_address(html):
    postal_code = ""
    address = ""

    candidates = re.findall(
        r'>([^<>]*〒\s*\d{3}-\d{4}[^<>]*)<',
        html,
        re.S,
    )

    if candidates:
        raw = clean(candidates[0])

        m = re.search(
            r'〒\s*(\d{3}-\d{4})',
            raw,
        )

        if m:
            postal_code = m.group(1)

        address = re.sub(
            r'^.*?〒\s*\d{3}-\d{4}\s*',
            "",
            raw,
        ).strip()

    if not address:
        for municipality in MUNICIPALITIES:
            m = re.search(
                rf'>([^<>]*'
                rf'{re.escape(municipality)}'
                rf'[^<>]*)<',
                html,
            )

            if m:
                address = clean(m.group(1))
                break

    return postal_code, address


def resolve_municipality(address):
    for name, code in MUNICIPALITIES.items():
        if name in address:
            return code, name

    raise ValueError(
        f"municipality not resolved: {address!r}"
    )


def extract_homepage(html):
    m = re.search(
        r'<dt\b[^>]*>\s*ホームページ\s*</dt>\s*'
        r'<dd\b[^>]*>.*?'
        r'<a\b[^>]*href="([^"]+)"',
        html,
        re.S,
    )

    if not m:
        return ""

    return unescape(m.group(1)).strip()


def extract_coordinates(html):
    m = re.search(
        r'id="mapTarget"[^>]*'
        r'value="\{&quot;pos&quot;:\['
        r'\s*([0-9.+-]+)\s*,'
        r'\s*([0-9.+-]+)\s*'
        r'\]\}"',
        html,
    )

    if not m:
        raise ValueError(
            "coordinates not found"
        )

    return m.group(1), m.group(2)


def extract_items(segment):
    result = []

    for raw in re.findall(
        r'<li\b[^>]*class="[^"]*'
        r'\bp-details__list__facility__item\b'
        r'[^"]*"[^>]*>(.*?)</li>',
        segment,
        re.S,
    ):
        text = clean(raw)

        if text:
            result.append(text)

    return result


def extract_remarks(segment):
    result = []

    for raw in re.findall(
        r'<section\b[^>]*class="[^"]*'
        r'\bp-details__remarks\b[^"]*"[^>]*>'
        r'(.*?)</section>',
        segment,
        re.S,
    ):
        text = clean(raw)
        text = re.sub(
            r"^備考\s*",
            "",
            text,
        )

        if text and text not in result:
            result.append(text)

    return result


def extract_survey_date(html):
    m = re.search(
        r'(?:調査日|調査年月日).*?'
        r'(\d{4})年\s*'
        r'(\d{1,2})月\s*'
        r'(\d{1,2})日',
        html,
        re.S,
    )

    if not m:
        return ""

    return (
        f"{int(m.group(1)):04d}-"
        f"{int(m.group(2)):02d}-"
        f"{int(m.group(3)):02d}"
    )


def main():
    files = sorted(
        INPUT_DIR.glob("detail-*.html")
    )

    urls = [
        line.strip()
        for line in URLS.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]

    assert len(files) == 1844
    assert len(urls) == 1844

    output_rows = []

    for path, source_url in zip(
        files,
        urls,
    ):
        html = path.read_text(
            encoding="utf-8"
        )

        segment = extract_toilet_segment(
            html
        )

        facility_name = first(
            r'id="titleName"\s+value="([^"]*)"',
            html,
        )

        source_row = first(
            r'id="faciCode"\s+value="([^"]*)"',
            html,
        )

        if not re.fullmatch(
            r"F\d{6}",
            source_row,
        ):
            raise ValueError(
                f"invalid faciCode: {source_row!r}"
            )

        postal_code, address = (
            extract_address(html)
        )

        municipality_code, municipality_name = (
            resolve_municipality(address)
        )

        latitude, longitude = (
            extract_coordinates(html)
        )

        items = extract_items(segment)
        remarks = extract_remarks(segment)

        combined = "\n".join(items)

        toilet_locations = []

        for item in items:
            if not item.startswith(
                "トイレの場所："
            ):
                continue

            value = item.split(
                "：",
                1,
            )[1].strip()

            if (
                value
                and value not in toilet_locations
            ):
                toilet_locations.append(value)

        attribute_notes = []

        if "男女共用である" in combined:
            attribute_notes.append(
                "男女共用トイレあり"
            )

        if "男女別である" in combined:
            attribute_notes.append(
                "男女別トイレあり"
            )

        if "緊急通報装置がある" in combined:
            attribute_notes.append(
                "緊急通報装置あり"
            )

        if "着替え台がある" in combined:
            attribute_notes.append(
                "着替え台あり"
            )

        survey_date = extract_survey_date(
            html
        )

        if survey_date:
            attribute_notes.append(
                f"調査日={survey_date}"
            )

        out = {
            "prefecture_code": "45",
            "prefecture_name": "宮崎県",
            "municipality_code": municipality_code,
            "municipality_name": municipality_name,
            "ward_name": "",

            "facility_name": facility_name,
            "formal_name": "",
            "facility_category": "",
            "postal_code": postal_code,
            "address": address,
            "latitude": latitude,
            "longitude": longitude,
            "homepage_url": extract_homepage(
                html
            ),

            "multipurpose_toilet": "yes",
            "wheelchair_toilet": "",
            "toilet_floor": " / ".join(
                toilet_locations
            ),
            "unisex_toilet_count": "",
            "male_toilet_count": "",
            "female_toilet_count": "",

            "washlet": (
                "yes"
                if (
                    "温水洗浄機付き便座である"
                    in combined
                )
                else ""
            ),
            "adult_bed": (
                "yes"
                if "介護用シートがある" in combined
                else ""
            ),
            "ostomate": (
                "yes"
                if (
                    "お湯洗浄のオストメイトがある"
                    in combined
                    or
                    "水洗浄のオストメイトがある"
                    in combined
                )
                else ""
            ),
            "voice_guidance": "",
            "baby_bed": (
                "yes"
                if "ベビーシートがある" in combined
                else ""
            ),
            "baby_chair": (
                "yes"
                if "ベビーチェアがある" in combined
                else ""
            ),
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

            "source_dataset": SOURCE_DATASET,
            "source_name": SOURCE_NAME,
            "source_url": source_url,
            "source_updated_at": "",
            "source_row": source_row,
            "attribute_note": " | ".join(
                attribute_notes
            ),
            "note": " | ".join(remarks),
        }

        output_rows.append(out)

    assert len(output_rows) == 1844
    assert len({
        r["source_row"]
        for r in output_rows
    }) == 1844
    assert len({
        r["source_url"]
        for r in output_rows
    }) == 1844

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

    print("input rows :", len(files))
    print("output rows:", len(output_rows))
    print("output     :", OUTPUT)


if __name__ == "__main__":
    main()
