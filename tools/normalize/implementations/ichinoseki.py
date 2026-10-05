#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.normalization import RowSupport
from tools.normalize.core.schema import read_schema_fields

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"
SRC = ROOT / "data/raw/03-岩手県/03209-一関市/public-toilet/03209_public-toilet.csv"
DEST = ROOT / "data/normalized/03-岩手県/03209-一関市/public-toilet/public-toilet.csv"

CODE5 = "03209"
NAME = "一関市"
EXPECTED_HEADER = [
    "No", "地域", "施設名", "所在地", "和式・洋式の別", "使用時間",
    "障がい者用トイレ", "赤ちゃんおむつ交換", "その他",
    "原点X", "原点Y", "原点(緯度)", "原点(経度)",
]

TIME_RANGES = {
    "7:00～19:00": ("07:00", "19:00"),
    "6：30～21：00": ("06:30", "21:00"),
    "8:30～16:45": ("08:30", "16:45"),
    "10：00～17：00": ("10:00", "17:00"),
    "9：00～16：00": ("09:00", "16:00"),
    "8：30～22：00": ("08:30", "22:00"),
}



def main():
    if not SRC.exists():
        raise RuntimeError(f"missing: {SRC}")
    if DEST.exists():
        raise RuntimeError(f"normalized already exists: {DEST}")

    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    with SRC.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        source_rows = list(reader)

    if header != EXPECTED_HEADER:
        raise RuntimeError(f"source header drift: {header!r}")
    if not source_rows:
        raise RuntimeError("source has no data rows")

    code6 = six_digit_municipality_code(CODE5)
    rows = []

    stat_24h = 0
    stat_ranges = 0
    stat_open = 0
    stat_office = 0

    for line_no, src in enumerate(source_rows, 2):
        clean = {k: (v or "").strip() for k, v in src.items()}

        row = {c: "" for c in schema}
        row["全国地方公共団体コード"] = code6
        row["地方公共団体名"] = NAME
        row["ID"] = clean["No"]
        row["名称"] = clean["施設名"]
        row["所在地_連結表記"] = clean["所在地"]
        row["所在地_都道府県"] = "岩手県"
        row["所在地_市区町村"] = NAME
        row["緯度"] = clean["原点(緯度)"]
        row["経度"] = clean["原点(経度)"]

        use_time = clean["使用時間"]

        if use_time in ("24時間", "2４時間"):
            row["利用開始時間"] = "00:00"
            row["利用終了時間"] = "23:59"
            RowSupport.append_text(row, "利用可能時間特記事項", use_time)
            if use_time == "2４時間":
                RowSupport.append_note(row, "原データ使用時間=2４時間")
            stat_24h += 1

        elif use_time in TIME_RANGES:
            start, end = TIME_RANGES[use_time]
            row["利用開始時間"] = start
            row["利用終了時間"] = end
            RowSupport.append_text(row, "利用可能時間特記事項", use_time)
            stat_ranges += 1

        elif use_time == "開館時間":
            RowSupport.append_text(row, "利用可能時間特記事項", use_time)
            stat_open += 1

        elif use_time == "開庁時間":
            RowSupport.append_text(row, "利用可能時間特記事項", use_time)
            stat_office += 1

        else:
            raise RuntimeError(
                f"line {line_no}: unexpected 使用時間={use_time!r}"
            )

        if clean["その他"]:
            RowSupport.append_text(row, "利用可能時間特記事項", clean["その他"])

        wheelchair = clean["障がい者用トイレ"]
        if wheelchair in ("有", "有（交流館側）"):
            row["車椅子使用者用トイレ有無"] = "有"
        elif wheelchair == "無":
            row["車椅子使用者用トイレ有無"] = "無"
        else:
            raise RuntimeError(
                f"line {line_no}: unexpected 障がい者用トイレ={wheelchair!r}"
            )

        diaper = clean["赤ちゃんおむつ交換"]
        if diaper in ("可", "有", "授乳室は可", "和室での対応", "可（交流館側）"):
            row["乳幼児用設備設置トイレ有無"] = "有"
        elif diaper in ("不可", "不", "不可(ベビーベッド無）"):
            row["乳幼児用設備設置トイレ有無"] = "無"
        else:
            raise RuntimeError(
                f"line {line_no}: unexpected 赤ちゃんおむつ交換={diaper!r}"
            )

        # Preserve source-specific wording in notes in addition to the
        # standardized yes/no equipment fields above.
        RowSupport.append_note(row, f"原データ地域={clean['地域']}")
        RowSupport.append_note(row, f"原データ和式・洋式の別={clean['和式・洋式の別']}")
        RowSupport.append_note(row, f"原データ障がい者用トイレ={clean['障がい者用トイレ']}")
        RowSupport.append_note(row, f"原データ赤ちゃんおむつ交換={clean['赤ちゃんおむつ交換']}")
        RowSupport.append_note(row, f"原データ原点X={clean['原点X']}")
        RowSupport.append_note(row, f"原データ原点Y={clean['原点Y']}")

        rows.append(row)

    ids = [r["ID"] for r in rows if r["ID"]]
    if len(ids) != len(rows) or len(ids) != len(set(ids)):
        raise RuntimeError(
            f"ID check failed: nonblank={len(ids)} unique={len(set(ids))}"
        )


    print("preflight OK: 一関市")
    print(
        f"rows={len(rows)} code={code6} "
        f"24h={stat_24h} ranges={stat_ranges} "
        f"open_hours={stat_open} office_hours={stat_office}"
    )

    DEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = DEST.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=schema, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(DEST)

    print(f"OK {CODE5} {NAME}: rows={len(rows)} encoding=utf-8-sig")


if __name__ == "__main__":
    main()
