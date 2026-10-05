#!/usr/bin/env python3

import csv
import html
import re
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from schema import FIELDS


ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = (
    ROOT
    / "data/raw/43-熊本県/barrier-free"
    / "kumamoto-odekake-anshin-toilet"
)
INPUT_LIST = SOURCE_ROOT / "all.csv"
PDF_DIR = SOURCE_ROOT / "pdfs"
MUNICIPALITY_MASTER = ROOT / "data/reference/municipalities.csv"

OUTPUT = (
    ROOT
    / "data/normalized/43-熊本県/barrier-free"
    / "kumamoto-odekake-anshin-toilet.csv"
)

SOURCE_NAME = "熊本県 おでかけ安心トイレ普及事業協力施設一覧"
SOURCE_DATASET = "odekake_anshin_toilet"

KUMAMOTO_CITY_AREAS = {
    "kumamoto-city-chuo": "中央区",
    "kumamoto-city-higashi": "東区",
    "kumamoto-city-nishi": "西区",
    "kumamoto-city-minami": "南区",
    "kumamoto-city-kita": "北区",
}

# 一覧側の住所が自治体判定に使えない、または詳細PDFで誤記を確認済みのものだけ補正。
ADDRESS_OVERRIDES = {
    "46688": "玉名市横島町横島3923",
    "46689": "玉名郡南関町大字下坂下1914-1",
}

# 元住所は変更せず、自治体判定だけに使う既知の表記ゆれ。
MUNICIPALITY_ADDRESS_ALIASES = {
    "菊池氏七城町": "菊池市",
}

MARKERS = {
    1: "①", 2: "②", 3: "③", 4: "④", 5: "⑤",
    6: "⑥", 7: "⑦", 8: "⑧", 9: "⑨", 10: "⑩",
    11: "⑪", 12: "⑫", 13: "⑬", 14: "⑭", 15: "⑮",
    16: "⑯", 17: "⑰", 18: "⑱", 19: "⑲", 20: "⑳",
}

LABELS = {
    1: "自動ドア",
    2: "便座の位置",
    3: "温水洗浄便座",
    4: "手すり",
    5: "背もたれクッション",
    6: "洗浄スイッチ",
    7: "洗面台の高さ",
    8: "蛇口",
    9: "鏡",
    10: "緊急呼び出しボタン",
    11: "多目的ベッド",
    12: "介護用カーテン",
    13: "化粧鏡",
    14: "汚物入れＢＯＸ",
    15: "手荷物用カウンター又はフック",
    16: "温水機能付きシャワー",
    17: "おむつ交換台",
    18: "ベビーチェア",
    19: "こども用便座",
    20: "授乳室",
}

COLUMNS = {
    "left": {
        "items": list(range(1, 13)),
        "xmin": 130,
        "xmax": 199.9,
    },
    "middle": {
        "items": list(range(13, 17)),
        "xmin": 340,
        "xmax": 395,
    },
    "right": {
        "items": list(range(17, 21)),
        "xmin": 495,
        "xmax": 590,
    },
}

WORD_RE = re.compile(
    r'<word xMin="([^"]+)" yMin="([^"]+)" '
    r'xMax="([^"]+)" yMax="([^"]+)">(.*?)</word>'
)

YES_EXACT = {"○", "〇", "有", "有り", "あり"}
NO_EXACT = {"×", "無", "無し", "なし"}
UNKNOWN_EXACT = {"", "-", "－"}


def clean(value):
    if value is None:
        return ""
    return " ".join(
        str(value)
        .replace("\f", " ")
        .replace("　", " ")
        .split()
    )


def list_mark(value):
    value = clean(value)
    if value in ("○", "〇"):
        return "yes"
    if value == "×":
        return "no"
    raise ValueError(f"unexpected list mark: {value!r}")


def equipment_presence(value):
    value = clean(value)
    if value in UNKNOWN_EXACT:
        return ""
    if value in YES_EXACT:
        return "yes"
    if value in NO_EXACT:
        return "no"

    # 「×(右側)」のような範囲限定の否定は施設全体の no にしない。
    if value.startswith("×(") or value.startswith("×（"):
        return ""

    # 注記付きの全面否定。
    if value.startswith("× ※") or value.startswith("×※"):
        return "no"

    # 設置場所・設置範囲が具体的に書かれているものは存在あり。
    return "yes"


def emergency_call(value):
    value = clean(value)
    if value in UNKNOWN_EXACT:
        return ""
    if "電話" in value:
        return "phone"
    if value in NO_EXACT:
        return "none"
    if value in YES_EXACT:
        return "button"
    raise ValueError(f"unsupported emergency call value: {value!r}")


def nursing_space(value):
    value = clean(value)
    if "別室で" in value and "授乳" in value:
        return "yes"
    return equipment_presence(value)


def pdf_id(url):
    return Path(urlparse(url).path).stem


def load_bbox(path):
    source = path.read_text(encoding="utf-8", errors="replace")
    words = []
    for m in WORD_RE.finditer(source):
        words.append({
            "x1": float(m.group(1)),
            "y1": float(m.group(2)),
            "x2": float(m.group(3)),
            "y2": float(m.group(4)),
            "text": html.unescape(m.group(5)),
        })
    return words


def find_anchors(words):
    anchors = {}
    for no, marker in MARKERS.items():
        if 1 <= no <= 12:
            xmin, xmax = 0, 140
        elif 13 <= no <= 16:
            xmin, xmax = 200, 340
        else:
            xmin, xmax = 390, 500

        hits = [
            w for w in words
            if w["text"].startswith(marker)
            and xmin <= w["x1"] <= xmax
        ]
        if len(hits) != 1:
            raise ValueError(
                f"item {no}: expected one anchor, got {len(hits)}"
            )
        anchors[no] = hits[0]
    return anchors


def join_words(words):
    words = sorted(words, key=lambda w: (w["y1"], w["x1"]))
    rows = []
    current = []
    current_y = None

    for word in words:
        if current_y is None or abs(word["y1"] - current_y) <= 2.0:
            current.append(word["text"])
            if current_y is None:
                current_y = word["y1"]
        else:
            rows.append(" ".join(current))
            current = [word["text"]]
            current_y = word["y1"]

    if current:
        rows.append(" ".join(current))

    return " | ".join(clean(row) for row in rows if clean(row))


def inline_anchor_value(no, word):
    text = clean(word["text"])
    prefixes = {
        1: "①自動ドア",
        2: "②便座の位置",
        3: "③温水洗浄便座",
        4: "④手すり",
        5: "⑤背もたれクッション",
        6: "⑥洗浄スイッチ",
        7: "⑦洗面台の高さ（cm）",
        8: "⑧蛇口",
        9: "⑨鏡",
        10: "⑩緊急呼び出しボタン",
        11: "⑪多目的ベッド",
        12: "⑫介護用カーテン",
        13: "⑬化粧鏡",
        14: "⑭汚物入れＢＯＸ",
        15: "⑮手荷物用カウンター",
        16: "⑯温水機能付きｼｬﾜｰ",
        17: "⑰おむつ交換台",
        18: "⑱ベビーチェア",
        19: "⑲こども用便座",
        20: "⑳授乳室",
    }
    prefix = prefixes[no]
    if text.startswith(prefix):
        return clean(text[len(prefix):])
    return ""


def parse_column(words, anchors, config):
    nums = config["items"]
    values = {}

    for idx, no in enumerate(nums):
        y = anchors[no]["y1"]

        if idx == 0:
            lower = y - 15
        else:
            previous = anchors[nums[idx - 1]]["y1"]
            lower = (previous + y) / 2

        if idx == len(nums) - 1:
            upper = y + 20
        else:
            following = anchors[nums[idx + 1]]["y1"]
            upper = (y + following) / 2

        candidates = [
            w for w in words
            if config["xmin"] <= w["x1"] <= config["xmax"]
            and lower <= w["y1"] < upper
        ]

        value = join_words(candidates)
        inline = inline_anchor_value(no, anchors[no])
        if inline:
            value = f"{inline} | {value}" if value else inline
        values[no] = value

    return values


def parse_pdf(pdf_path, workdir):
    bbox_path = workdir / f"{pdf_path.stem}.html"
    subprocess.run(
        ["pdftotext", "-bbox-layout", str(pdf_path), str(bbox_path)],
        check=True,
    )
    words = load_bbox(bbox_path)
    anchors = find_anchors(words)
    values = {}
    for config in COLUMNS.values():
        values.update(parse_column(words, anchors, config))
    return values


def attribute_note(values, pdf_url, original_address, effective_address):
    entries = []
    for no in range(1, 21):
        value = clean(values.get(no))
        if value:
            entries.append(f"{MARKERS[no]}{LABELS[no]}={value}")

    entries.append(f"detail_pdf={pdf_url}")

    if clean(original_address) == "同上":
        entries.append(f"list_address=同上; inherited_address={effective_address}")
    elif clean(original_address) != clean(effective_address):
        entries.append(
            f"list_address={clean(original_address)}; "
            f"corrected_address={clean(effective_address)}"
        )

    return "; ".join(entries)


def load_municipalities():
    with MUNICIPALITY_MASTER.open(
        encoding="utf-8-sig",
        newline="",
    ) as f:
        rows = [
            r for r in csv.DictReader(f)
            if clean(r.get("prefecture_code")) == "43"
        ]

    by_name = {
        clean(r["municipality_name"]): r
        for r in rows
        if clean(r.get("municipality_name"))
    }
    return rows, by_name


def resolve_municipality(row, address, municipalities, by_name):
    area = clean(row["area"])

    if area in KUMAMOTO_CITY_AREAS:
        return "43100", "熊本市", KUMAMOTO_CITY_AREAS[area]

    for source, municipality_name in MUNICIPALITY_ADDRESS_ALIASES.items():
        if source in address:
            m = by_name[municipality_name]
            return clean(m["municipality_code"]), municipality_name, ""

    candidates = []
    for m in municipalities:
        municipality_name = clean(m["municipality_name"])
        parent = clean(m.get("parent_name"))

        if not municipality_name or municipality_name == "熊本市":
            continue

        full = parent + municipality_name if parent else municipality_name
        if full and full in address:
            candidates.append((len(full), municipality_name, m))
        elif municipality_name in address:
            candidates.append((len(municipality_name), municipality_name, m))

    if not candidates:
        raise ValueError(
            f"municipality not found: area={area!r} "
            f"facility={row['facility_name']!r} address={address!r}"
        )

    max_len = max(item[0] for item in candidates)
    best = [item for item in candidates if item[0] == max_len]
    names = {item[1] for item in best}
    if len(names) != 1:
        raise ValueError(
            f"ambiguous municipality: facility={row['facility_name']!r} "
            f"address={address!r} candidates={sorted(names)!r}"
        )

    _, municipality_name, m = best[0]
    return clean(m["municipality_code"]), municipality_name, ""


def effective_addresses(rows):
    out = []
    previous_by_area = {}

    for row in rows:
        area = clean(row["area"])
        original = clean(row["address"])
        detail_id = pdf_id(row["pdf_url"])

        if detail_id in ADDRESS_OVERRIDES:
            effective = ADDRESS_OVERRIDES[detail_id]
        elif original == "同上":
            effective = previous_by_area.get(area, "")
            if not effective:
                raise ValueError(
                    f"cannot inherit 同上 address: {detail_id} {row['facility_name']!r}"
                )
        else:
            effective = original

        if not effective:
            raise ValueError(
                f"blank effective address: {detail_id} {row['facility_name']!r}"
            )

        previous_by_area[area] = effective
        out.append(effective)

    return out


def main():
    with INPUT_LIST.open(encoding="utf-8-sig", newline="") as f:
        source_rows = list(csv.DictReader(f))

    assert len(source_rows) == 855

    required = {
        "area", "page_url", "facility_name", "address",
        "wheelchair", "ostomate", "baby_bed", "phone", "pdf_url",
    }
    missing = required - set(source_rows[0])
    if missing:
        raise ValueError(f"input columns missing: {sorted(missing)}")

    ids = [pdf_id(row["pdf_url"]) for row in source_rows]
    assert len(ids) == 855
    assert len(ids) == len(set(ids))

    addresses = effective_addresses(source_rows)
    municipalities, by_name = load_municipalities()
    output_rows = []

    with tempfile.TemporaryDirectory(prefix="kumamoto-barrier-free-") as tmp:
        workdir = Path(tmp)

        for index, (row, effective_address) in enumerate(
            zip(source_rows, addresses),
            start=1,
        ):
            facility = clean(row["facility_name"])
            detail_id = pdf_id(row["pdf_url"])
            pdf_path = PDF_DIR / f"{detail_id}.pdf"

            if not pdf_path.is_file():
                raise FileNotFoundError(pdf_path)

            municipality_code, municipality_name, ward_name = resolve_municipality(
                row,
                effective_address,
                municipalities,
                by_name,
            )

            values = parse_pdf(pdf_path, workdir)

            # 47328 イオン天草店:
            # PDFでは「⑲こども用便座○（女性用トイレのみ）」と確認済み。
            # bboxではラベルと値の境界の都合で値を回収できないため明示補正。
            if detail_id == "47328" and not clean(values.get(19)):
                values[19] = "○（女性用トイレのみ）"

            washlet = equipment_presence(values[3])
            adult_bed = equipment_presence(values[11])
            baby_chair = equipment_presence(values[18])
            child_toilet = equipment_presence(values[19])
            nursing = nursing_space(values[20])
            emergency = emergency_call(values[10])

            # 47328 は「⑲こども用便座○（女性用トイレのみ）」が1 wordに結合。
            # inline_anchor_value() で ○（女性用トイレのみ）を回収できるため yes になる。
            if detail_id == "47328" and child_toilet != "yes":
                raise AssertionError(
                    f"47328 child_toilet parse failed: {values[19]!r}"
                )

            out = {
                "prefecture_code": "43",
                "prefecture_name": "熊本県",
                "municipality_code": municipality_code,
                "municipality_name": municipality_name,
                "ward_name": ward_name,

                "facility_name": facility,
                "formal_name": "",
                "facility_category": "",
                "postal_code": "",
                "address": effective_address,
                "latitude": "",
                "longitude": "",
                "homepage_url": "",

                # 一覧に車いす対応があっても「多目的」とは推測しない。
                "multipurpose_toilet": "",
                "wheelchair_toilet": list_mark(row["wheelchair"]),
                "toilet_floor": "",
                "unisex_toilet_count": "",
                "male_toilet_count": "",
                "female_toilet_count": "",

                "washlet": washlet,
                "adult_bed": adult_bed,
                "ostomate": list_mark(row["ostomate"]),
                "voice_guidance": "",
                # ⑰はおむつ交換台であり baby_bed とは推測しない。
                "baby_bed": "",
                "baby_chair": baby_chair,
                "child_toilet": child_toilet,
                "child_chair": "",
                # ⑥洗浄スイッチ（自動/手動）は flush_type とはみなさない。
                "flush_type": "",
                "emergency_call_type": emergency,

                "male_urinal_with_rail": "",
                "male_western_toilet": "",
                "female_western_toilet": "",
                "male_baby_bed": "",
                "female_baby_bed": "",
                "male_baby_chair": "",
                "female_baby_chair": "",

                "entrance_step": "",
                "stroller_rental": "",
                "nursing_space": nursing,
                # 一覧の「おむつ交換台付きトイレ」をそのまま採用。
                "diaper_changing_space": list_mark(row["baby_bed"]),
                "kids_room": "",

                "source_dataset": SOURCE_DATASET,
                "source_name": SOURCE_NAME,
                "source_url": clean(row["page_url"]),
                "source_updated_at": "",
                "source_row": detail_id,
                "attribute_note": attribute_note(
                    values,
                    clean(row["pdf_url"]),
                    clean(row["address"]),
                    effective_address,
                ),
                "note": "",
            }

            output_rows.append(out)

            if index % 100 == 0:
                print(f"parsed {index}/855")

    assert len(output_rows) == 855
    assert all(set(r) == set(FIELDS) for r in output_rows)
    assert len({r["source_row"] for r in output_rows}) == 855

    # 一覧3項目は正規化後も完全一致すること。
    for src, out in zip(source_rows, output_rows):
        assert out["wheelchair_toilet"] == list_mark(src["wheelchair"])
        assert out["ostomate"] == list_mark(src["ostomate"])
        assert out["diaper_changing_space"] == list_mark(src["baby_bed"])

    # 自治体解決は全件必須。
    assert all(r["municipality_code"] for r in output_rows)
    assert all(r["municipality_name"] for r in output_rows)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output_rows)

    print()
    print("input rows :", len(source_rows))
    print("output rows:", len(output_rows))
    print("columns    :", len(FIELDS))
    print("output     :", OUTPUT)

    print()
    print("=== area counts ===")
    for area, count in sorted(Counter(r["area"] for r in source_rows).items()):
        print(f"{area:22} {count}")

    print()
    print("=== municipality counts ===")
    for (code, name), count in sorted(
        Counter(
            (r["municipality_code"], r["municipality_name"])
            for r in output_rows
        ).items()
    ):
        print(f"{code} {name:10} {count}")

    for field in (
        "wheelchair_toilet",
        "ostomate",
        "diaper_changing_space",
        "washlet",
        "adult_bed",
        "baby_chair",
        "child_toilet",
        "emergency_call_type",
        "nursing_space",
    ):
        print()
        print(field, dict(Counter(r[field] for r in output_rows)))


if __name__ == "__main__":
    main()
