#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from html import unescape
from pathlib import Path

from schema import FIELDS


ROOT = Path(__file__).resolve().parents[3]

RAW_DIR = (
    ROOT
    / "data/raw/47-沖縄県/barrier-free/okinawa-barrier-free-map/details"
)

OUTPUT = (
    ROOT
    / "data/normalized/47-沖縄県/barrier-free/"
    "okinawa-barrier-free-map.csv"
)

SOURCE_NAME = "沖縄県バリアフリーマップ"
SOURCE_DATASET = "barrier_free_map"
SOURCE_BASE_URL = "http://okinawa-bf-map.jp/facility-info/detail?facility_id="

EXPECTED_RAW_FILES = 2171
EXPECTED_OUTPUT_ROWS = 2099

MUNICIPALITIES = {
    "那覇市": "47201",
    "宜野湾市": "47205",
    "石垣市": "47207",
    "浦添市": "47208",
    "名護市": "47209",
    "糸満市": "47210",
    "沖縄市": "47211",
    "豊見城市": "47212",
    "うるま市": "47213",
    "宮古島市": "47214",
    "南城市": "47215",
    "国頭村": "47301",
    "大宜味村": "47302",
    "東村": "47303",
    "今帰仁村": "47306",
    "本部町": "47308",
    "恩納村": "47311",
    "宜野座村": "47313",
    "金武町": "47314",
    "伊江村": "47315",
    "読谷村": "47324",
    "嘉手納町": "47325",
    "北谷町": "47326",
    "北中城村": "47327",
    "中城村": "47328",
    "西原町": "47329",
    "与那原町": "47348",
    "南風原町": "47350",
    "渡嘉敷村": "47353",
    "座間味村": "47354",
    "粟国村": "47355",
    "渡名喜村": "47356",
    "南大東村": "47357",
    "北大東村": "47358",
    "伊平屋村": "47359",
    "伊是名村": "47360",
    "久米島町": "47361",
    "八重瀬町": "47362",
    "多良間村": "47375",
    "竹富町": "47381",
    "与那国町": "47382",
}

MAJOR_TOILET_FIELDS = {
    "多目的トイレ",
    "車いす利用可能トイレ",
    "オストメイト対応",
    "温水洗浄便座",
    "和式",
    "洋式",
    "洋式手すり",
    "緊急通報装置",
    "ユニバーサルシート",
    "ベビーベッド",
    "ベビーチェア",
}

# 主要トイレ項目が無いが、備考・マークから採用する2施設。
EXCEPTION_IDS = {
    "形成外科KC": "wheelchair",
    "しののめ保育園": "child",
}


def clean(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " / ", value or "", flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(unescape(value).split())


def table_pairs(html: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}

    for raw_key, raw_value in re.findall(
        r'<td[^>]*class="title-rpd"[^>]*>\s*(.*?)\s*</td>\s*'
        r'<td[^>]*>\s*(.*?)\s*</td>',
        html,
        re.S,
    ):
        key = clean(raw_key)
        value = clean(raw_value)

        if key:
            result.setdefault(key, []).append(value)

    return result


def first(values: dict[str, list[str]], key: str) -> str:
    items = values.get(key, [])
    return items[0] if items else ""


def yes_no(value: str) -> str:
    value = value.strip()

    if value in {"有", "対応"}:
        return "yes"
    if value in {"無", "非対応"}:
        return "no"

    raise RuntimeError(f"unsupported yes/no value: {value!r}")


def direct_yes_no(values: dict[str, list[str]], key: str) -> str:
    raw = first(values, key)
    if not raw:
        return ""
    return yes_no(raw)


def grouped_baby(values: dict[str, list[str]], keys: list[str]) -> str:
    found: list[str] = []

    for key in keys:
        found.extend(values.get(key, []))

    if not found:
        return ""

    # 「女性用トイレあり」「多目的トイレあり」等も設備あり。
    if any(
        value == "有" or "あり" in value
        for value in found
    ):
        return "yes"

    if all(value == "無" for value in found):
        return "no"

    raise RuntimeError(
        f"unsupported baby equipment values: {keys!r}: {found!r}"
    )


def parse_name(html: str) -> str:
    m = re.search(r"<h3>\s*(.*?)\s*</h3>", html, re.S)
    if not m:
        raise RuntimeError("facility name not found")
    return clean(m.group(1))


def parse_updated(html: str) -> str:
    m = re.search(
        r"最終更新日:\s*(\d{4}-\d{2}-\d{2})",
        html,
    )
    if not m:
        raise RuntimeError("updated date not found")
    return m.group(1)


def parse_address(html: str) -> tuple[str, str]:
    m = re.search(
        r'>所在地</td>\s*<td[^>]*>(.*?)</td>',
        html,
        re.S,
    )
    if not m:
        raise RuntimeError("address not found")

    raw = clean(m.group(1))

    postal = ""
    pm = re.search(r"〒\s*(\d{3}-\d{4})", raw)
    if pm:
        postal = pm.group(1)

    address = re.sub(r"^〒\s*\d{3}-\d{4}\s*/\s*", "", raw)
    address = re.sub(r"^〒\s*/\s*", "", address)
    address = address.strip(" /")

    return postal, address


def parse_coordinates(html: str) -> tuple[str, str]:
    m = re.search(
        r"new google\.maps\.LatLng\(\s*"
        r"([0-9.]+)\s*,\s*([0-9.]+)\s*\)",
        html,
    )
    if not m:
        raise RuntimeError("coordinates not found")

    latitude = m.group(1)
    longitude = m.group(2)

    # The source site uses (0, 0) for facilities whose coordinates are
    # unavailable. Do not expose it as a real location in normalized data.
    try:
        if float(latitude) == 0.0 and float(longitude) == 0.0:
            return "", ""
    except ValueError:
        pass

    return latitude, longitude


def parse_homepage(values: dict[str, list[str]], html: str) -> str:
    m = re.search(
        r'>URL</td>\s*<td[^>]*>\s*'
        r'<a[^>]+href="([^"]+)"',
        html,
        re.S,
    )
    return unescape(m.group(1)).strip() if m else ""


def resolve_municipality(
    name: str,
    address: str,
    latitude: str,
    longitude: str,
) -> tuple[str, str]:
    for municipality, code in MUNICIPALITIES.items():
        if municipality in address:
            return municipality, code

    # 県名省略等の既知6件。
    overrides = {
        "東風平運動公園ソフトボール場": "八重瀬町",
        "糸数区公民館": "南城市",
        "新車量販店 Ｆシステム沖縄本店": "宜野湾市",
        "国際通り": "那覇市",
        "金武町立金武保育所": "金武町",
        "マックスバリュ金武店": "金武町",
    }

    municipality = overrides.get(name)
    if municipality:
        return municipality, MUNICIPALITIES[municipality]

    raise RuntimeError(
        "municipality unresolved: "
        f"name={name!r} address={address!r} "
        f"lat={latitude} lon={longitude}"
    )


def parse_note(values: dict[str, list[str]]) -> str:
    notes = []

    for key in ("特徴･注意点", "備考", "トイレ備考"):
        for value in values.get(key, []):
            if value and value not in notes:
                notes.append(f"{key}: {value}")

    return " / ".join(notes)


def build_attribute_note(values: dict[str, list[str]]) -> str:
    notes = []

    emergency = first(values, "緊急通報装置")
    if emergency == "有":
        notes.append("緊急通報装置あり")

    changing = first(values, "着替え台")
    if changing == "有":
        notes.append("着替え台あり")

    toilet_shape = first(values, "トイレ出入口形状")
    if toilet_shape:
        notes.append(f"トイレ出入口形状={toilet_shape}")

    return " / ".join(notes)


def should_include(
    name: str,
    values: dict[str, list[str]],
) -> bool:
    if set(values) & MAJOR_TOILET_FIELDS:
        return True

    return name in EXCEPTION_IDS


def normalize_one(path: Path) -> dict[str, str] | None:
    html = path.read_text(encoding="utf-8")
    values = table_pairs(html)

    name = parse_name(html)

    if not should_include(name, values):
        return None

    facility_id = path.stem

    if not re.fullmatch(r"\d+", facility_id):
        raise RuntimeError(f"invalid facility id: {facility_id!r}")

    postal_code, address = parse_address(html)
    latitude, longitude = parse_coordinates(html)
    municipality_name, municipality_code = resolve_municipality(
        name,
        address,
        latitude,
        longitude,
    )

    row = {field: "" for field in FIELDS}

    row["prefecture_code"] = "47"
    row["prefecture_name"] = "沖縄県"
    row["municipality_code"] = municipality_code
    row["municipality_name"] = municipality_name
    row["facility_name"] = name
    row["postal_code"] = postal_code
    row["address"] = address
    row["latitude"] = latitude
    row["longitude"] = longitude
    row["homepage_url"] = parse_homepage(values, html)

    row["multipurpose_toilet"] = direct_yes_no(
        values, "多目的トイレ"
    )
    row["wheelchair_toilet"] = direct_yes_no(
        values, "車いす利用可能トイレ"
    )
    row["washlet"] = direct_yes_no(
        values, "温水洗浄便座"
    )
    row["adult_bed"] = direct_yes_no(
        values, "ユニバーサルシート"
    )
    row["ostomate"] = direct_yes_no(
        values, "オストメイト対応"
    )
    row["voice_guidance"] = direct_yes_no(
        values, "音声案内"
    )

    row["baby_bed"] = grouped_baby(
        values,
        [
            "ベビーベッド",
            "洋式ベビーベッド",
        ],
    )

    row["baby_chair"] = grouped_baby(
        values,
        [
            "ベビーチェア",
            "洋式ベビーチェア",
            "トイレ外ベビーチェア",
        ],
    )

    row["nursing_space"] = direct_yes_no(
        values, "授乳室"
    )
    row["stroller_rental"] = direct_yes_no(
        values, "ベビーカー"
    )
    row["kids_room"] = direct_yes_no(
        values, "キッズスペース"
    )

    # 建物一般の「段差」ではなく、トイレ出入口段差を使用。
    row["entrance_step"] = direct_yes_no(
        values, "トイレ出入口段差"
    )

    # sourceが装置の種類までは示していないため空欄。
    row["emergency_call_type"] = ""

    # 主要項目なしの例外2件。
    exception = EXCEPTION_IDS.get(name)

    if exception == "wheelchair":
        row["wheelchair_toilet"] = "yes"

    if exception == "child":
        row["child_toilet"] = "yes"

        # 詳細ページの福祉マークに授乳室あり。
        if not row["nursing_space"]:
            row["nursing_space"] = "yes"

    row["source_dataset"] = SOURCE_DATASET
    row["source_name"] = SOURCE_NAME
    row["source_url"] = SOURCE_BASE_URL + facility_id
    row["source_updated_at"] = parse_updated(html)
    row["source_row"] = facility_id
    row["attribute_note"] = build_attribute_note(values)
    row["note"] = parse_note(values)

    return row


def main() -> None:
    files = sorted(RAW_DIR.glob("*.html"))

    if len(files) != EXPECTED_RAW_FILES:
        raise RuntimeError(
            f"raw files={len(files)} expected={EXPECTED_RAW_FILES}"
        )

    if len(FIELDS) != 48:
        raise RuntimeError(
            f"schema columns={len(FIELDS)} expected=48"
        )

    rows = []

    for path in files:
        row = normalize_one(path)
        if row is not None:
            rows.append(row)

    if len(rows) != EXPECTED_OUTPUT_ROWS:
        raise RuntimeError(
            f"normalized rows={len(rows)} "
            f"expected={EXPECTED_OUTPUT_ROWS}"
        )

    source_rows = [row["source_row"] for row in rows]
    if len(source_rows) != len(set(source_rows)):
        raise RuntimeError("duplicate source_row")

    source_urls = [row["source_url"] for row in rows]
    if len(source_urls) != len(set(source_urls)):
        raise RuntimeError("duplicate source_url")

    for row in rows:
        if not row["facility_name"]:
            raise RuntimeError("blank facility_name")
        if not row["municipality_code"]:
            raise RuntimeError(
                f"blank municipality: {row['facility_name']}"
            )
        if bool(row["latitude"]) != bool(row["longitude"]):
            raise RuntimeError(
                f"one-sided coordinates: {row['facility_name']}"
            )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

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
        writer.writerows(rows)

    print(f"OK rows={len(rows)}")
    print(f"output={OUTPUT}")


if __name__ == "__main__":
    main()
