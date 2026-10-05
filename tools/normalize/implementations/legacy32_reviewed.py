#!/usr/bin/env python3
from __future__ import annotations
from tools.normalize.core.normalization import RowSupport, StandardCsvWriter

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from tools.normalize.core.schema import read_schema_fields

ROOT = Path.cwd()
SCHEMA_PATH = ROOT / "schema/standard/public-toilet/schema.csv"
RAW = ROOT / "data/raw"
OUT = ROOT / "data/normalized"

TARGETS = {
    "23207": {
        "name": "豊川市", "pref": "23-愛知県", "file": "23207_public-toilet.csv", "code6": "232076",
    },
    "26204": {
        "name": "宇治市", "pref": "26-京都府", "file": "26204_public-toilet.csv", "code6": "262048",
    },
    "27215": {
        "name": "寝屋川市", "pref": "27-大阪府", "file": "27215_public-toilet.csv", "code6": "272159",
    },
    "39206": {
        "name": "須崎市", "pref": "39-高知県", "file": "39206_public-toilet.csv", "code6": "392065",
    },
    "39208": {
        "name": "宿毛市", "pref": "39-高知県", "file": "392081_public_toilet.csv", "code6": "392081",
    },
    "39210": {
        "name": "四万十市", "pref": "39-高知県", "file": "11296.csv", "code6": "392103",
    },
    "47327": {
        "name": "北中城村", "pref": "47-沖縄県", "file": "47327_public-toilet.csv", "code6": "473278",
    },
}

CODE_VARIANTS = ("都道府県コード又は市区町村コード", "市区町村コード")

LEGACY_MAP = {
    "名称": "名称",
    "名称_カナ": "名称_カナ",
    "名称_英語": "名称_英語",
    "設置位置": "設置位置",
    "緯度": "緯度",
    "経度": "経度",
    "男性トイレ総数": "男性トイレ総数",
    "男性トイレ数（小便器）": "男性トイレ数（小便器）",
    "男性トイレ数（和式）": "男性トイレ数（和式）",
    "男性トイレ数（洋式）": "男性トイレ数（洋式）",
    "女性トイレ総数": "女性トイレ総数",
    "女性トイレ数（和式）": "女性トイレ数（和式）",
    "女性トイレ数（洋式）": "女性トイレ数（洋式）",
    "男女共用トイレ総数": "男女共用トイレ総数",
    "男女共用トイレ数（和式）": "男女共用トイレ数（和式）",
    "男女共用トイレ数（洋式）": "男女共用トイレ数（洋式）",
    "車椅子使用者用トイレ有無": "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無": "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無": "オストメイト設置トイレ有無",
    "利用開始時間": "利用開始時間",
    "利用終了時間": "利用終了時間",
    "利用可能時間特記事項": "利用可能時間特記事項",
    "画像": "画像",
    "画像_ライセンス": "画像_ライセンス",
    "備考": "備考",
}


def detect_encoding(path: Path):
    b = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            b.decode(enc)
            return enc
        except UnicodeDecodeError:
            pass
    raise RuntimeError(f"cannot decode: {path}")


def read_rows(path: Path):
    enc = detect_encoding(path)
    with path.open("r", encoding=enc, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        rows = []
        for line_no, src in enumerate(reader, 2):
            if None in src:
                raise RuntimeError(
                    f"{path.name}:{line_no}: physical row has overflow columns: {src[None]!r}"
                )
            clean = {k: (v or "").strip() for k, v in src.items()}
            if not any(clean.values()):
                continue
            clean["_line"] = str(line_no)
            rows.append(clean)
    return enc, header, rows


def normalize_simple_time(value: str) -> str:
    s = (value or "").strip().replace("：", ":")
    if not s:
        return ""
    m = re.fullmatch(r"(\d{1,2}):(\d{2})(?::00)?", s)
    if not m:
        return s
    hh, mm = int(m.group(1)), int(m.group(2))
    if 0 <= hh <= 23 and 0 <= mm <= 59:
        return f"{hh:02d}:{mm:02d}"
    return s


def excel_date_time(value: str):
    s = (value or "").strip()
    m = re.fullmatch(r"1899/12/30\s+(\d{1,2}):(\d{2}):(\d{2})", s)
    if not m:
        return None
    hh, mm, ss = map(int, m.groups())
    if ss != 0 or not (0 <= hh <= 23 and 0 <= mm <= 59):
        raise RuntimeError(f"unexpected Excel time: {s!r}")
    return f"{hh:02d}:{mm:02d}"


def japanese_dms(value: str, axis: str):
    s = (value or "").strip()
    if not s:
        return None

    if axis == "lat":
        m = re.fullmatch(r"(北緯|南緯)(\d+)度(\d+)分(\d+(?:\.\d+)?)秒", s)
        if not m:
            return None
        sign = -1 if m.group(1) == "南緯" else 1
    else:
        m = re.fullmatch(r"(東経|西経)(\d+)度(\d+)分(\d+(?:\.\d+)?)秒", s)
        if not m:
            return None
        sign = -1 if m.group(1) == "西経" else 1

    deg = float(m.group(2))
    minute = float(m.group(3))
    sec = float(m.group(4))
    decimal = sign * (deg + minute / 60 + sec / 3600)
    return f"{decimal:.6f}"


def bool_from_numeric(row, field):
    v = (row.get(field) or "").strip()
    if not v.isdigit():
        return False
    RowSupport.append_text(row, "備考", f"原データ{field}={v}")
    row[field] = "無" if int(v) == 0 else "有"
    return True


def base_row(src, schema, cfg):
    row = {c: src.get(c, "") for c in schema}

    for old, new in LEGACY_MAP.items():
        if old in src:
            row[new] = src.get(old, "")

    code_value = ""
    for col in CODE_VARIANTS:
        if src.get(col):
            code_value = src[col].replace(",", "").strip()
            break
    if code_value and code_value != cfg["code6"]:
        raise RuntimeError(
            f"{cfg['name']} line {src['_line']}: source code={code_value!r} "
            f"expected={cfg['code6']!r}"
        )

    row["全国地方公共団体コード"] = cfg["code6"]
    row["所在地_全国地方公共団体コード"] = cfg["code6"]
    row["地方公共団体名"] = cfg["name"]

    if src.get("都道府県名"):
        row["所在地_都道府県"] = src["都道府県名"]
    if src.get("市区町村名"):
        row["所在地_市区町村"] = src["市区町村名"]
    if src.get("住所"):
        row["所在地_連結表記"] = src["住所"]
    if src.get("方書"):
        row["建物名等(方書)"] = src["方書"]

    row["ID"] = src.get("NO", "")

    multi = src.get("多機能トイレ数", "")
    if multi:
        RowSupport.append_text(row, "備考", f"原データ多機能トイレ数={multi}")

    row["利用開始時間"] = normalize_simple_time(row["利用開始時間"])
    row["利用終了時間"] = normalize_simple_time(row["利用終了時間"])

    return row


def normalize_target(code, cfg, schema):
    src_path = RAW / cfg["pref"] / f"{code}-{cfg['name']}" / "public-toilet" / cfg["file"]
    dest = OUT / cfg["pref"] / f"{code}-{cfg['name']}" / "public-toilet/public-toilet.csv"

    if not src_path.exists():
        raise RuntimeError(f"{code}: missing raw: {src_path}")
    if dest.exists():
        raise RuntimeError(f"{code}: normalized already exists: {dest}")

    enc, header, src_rows = read_rows(src_path)

    # All seven are the same legacy family: 32 physical columns.
    if len(header) != 32:
        raise RuntimeError(f"{code}: header columns={len(header)} expected=32")

    if code == "47327":
        src_rows = [
            src for src in src_rows
            if (src.get("名称") or "").strip()
        ]

    out = [base_row(src, schema, cfg) for src in src_rows]

    # 豊川市: source NO 81 appears three times. Keep source NO in 備考 and
    # create deterministic suffixed IDs only for that duplicate group.
    if code == "23207":
        counts = Counter(r.get("NO", "") for r in src_rows if r.get("NO"))
        if counts.get("81") != 3:
            raise RuntimeError(f"豊川市: expected NO=81 x3, got {counts.get('81')}")
        seen = defaultdict(int)
        for src, row in zip(src_rows, out):
            no = src.get("NO", "")
            if counts.get(no, 0) > 1:
                seen[no] += 1
                RowSupport.append_text(row, "備考", f"原データNO={no}")
                row["ID"] = f"{no}_{seen[no]}"

    # 宇治市:
    # - 多機能トイレ数 is 有/無 rather than a number. It is source-only
    #   metadata and is already preserved in 備考 by base_row.
    # - count fields use the placeholder "ー" for unknown/not supplied values.
    #   Preserve the source value in 備考 and leave the standardized count blank.
    elif code == "26204":
        unexpected_multi = sorted({
            src.get("多機能トイレ数", "")
            for src in src_rows
            if src.get("多機能トイレ数", "") not in ("", "有", "無")
        })
        if unexpected_multi:
            raise RuntimeError(
                f"宇治市: unexpected 多機能 values={unexpected_multi!r}"
            )

        count_fields = (
            "男性トイレ総数",
            "男性トイレ数（小便器）",
            "男性トイレ数（和式）",
            "男性トイレ数（洋式）",
            "女性トイレ総数",
            "女性トイレ数（和式）",
            "女性トイレ数（洋式）",
            "男女共用トイレ総数",
            "男女共用トイレ数（和式）",
            "男女共用トイレ数（洋式）",
            "バリアフリートイレ数",
        )
        for row in out:
            for field in count_fields:
                if (row.get(field) or "").strip() == "ー":
                    RowSupport.append_text(row, "備考", f"原データ{field}=ー")
                    row[field] = ""

    # 寝屋川市:
    # - 乳幼児用設備設置トイレ有無 is supplied as numeric 0/2.
    # - 24時間使用可能 is descriptive text in start-time field.
    # - one seasonal schedule is descriptive text.
    elif code == "27215":
        for src, row in zip(src_rows, out):
            bool_from_numeric(row, "乳幼児用設備設置トイレ有無")

            raw_start = src.get("利用開始時間", "")
            if raw_start == "24時間使用可能":
                row["利用開始時間"] = "00:00"
                row["利用終了時間"] = "23:59"
                RowSupport.append_text(
                    row, "利用可能時間特記事項",
                    "原データ利用開始時間=24時間使用可能"
                )
            elif raw_start:
                row["利用開始時間"] = ""
                row["利用終了時間"] = ""
                RowSupport.append_text(
                    row, "利用可能時間特記事項",
                    f"原データ利用開始時間={raw_start}"
                )

    # 須崎市:
    # - three duplicate NO pairs originate from separate departmental blocks.
    # - numeric 1/2 in boolean columns means presence/count-like source data;
    #   positive values can safely be normalized to 有 while preserving originals.
    elif code == "39206":
        counts = Counter(r.get("NO", "") for r in src_rows if r.get("NO"))
        expected_dupes = {"080000001": 2, "080000002": 2, "080000003": 2}
        actual_dupes = {k: v for k, v in counts.items() if v > 1}
        if actual_dupes != expected_dupes:
            raise RuntimeError(f"須崎市 duplicate NO mismatch: {actual_dupes}")

        seen = defaultdict(int)
        for src, row in zip(src_rows, out):
            no = src.get("NO", "")
            if counts.get(no, 0) > 1:
                seen[no] += 1
                RowSupport.append_text(row, "備考", f"原データNO={no}")
                row["ID"] = f"{no}_{seen[no]}"

            for field in (
                "車椅子使用者用トイレ有無",
                "乳幼児用設備設置トイレ有無",
                "オストメイト設置トイレ有無",
            ):
                bool_from_numeric(row, field)
    # 宿毛市:
    # strip the Excel serial-date artifact from time fields. For rows explicitly
    # marked "24時間利用可能" with 00:00→00:00, normalize end to 23:59.
    elif code == "39208":
        for src, row in zip(src_rows, out):
            for field in ("利用開始時間", "利用終了時間"):
                raw = src.get(field, "")
                converted = excel_date_time(raw)
                if converted is not None:
                    RowSupport.append_text(row, "備考", f"原データ{field}={raw}")
                    row[field] = converted

            if (
                "24時間利用可能" in (row.get("利用可能時間特記事項") or "")
                and row.get("利用開始時間") == "00:00"
                and row.get("利用終了時間") == "00:00"
            ):
                row["利用終了時間"] = "23:59"

    # 四万十市 needs no extra mutation here: "-" in 多機能トイレ数 is
    # source-only metadata already preserved in 備考 by base_row.
    # 北中城村:
    # convert Japanese degree-minute-second coordinate strings to decimal degrees.
    elif code == "47327":
        for src, row in zip(src_rows, out):
            raw_lat = src.get("緯度", "")
            raw_lon = src.get("経度", "")

            lat = japanese_dms(raw_lat, "lat")
            lon = japanese_dms(raw_lon, "lon")

            if raw_lat and lat is None:
                raise RuntimeError(
                    f"北中城村 line {src['_line']}: unsupported latitude={raw_lat!r}"
                )
            if raw_lon and lon is None:
                raise RuntimeError(
                    f"北中城村 line {src['_line']}: unsupported longitude={raw_lon!r}"
                )

            if lat is not None:
                RowSupport.append_text(row, "備考", f"原データ緯度={raw_lat}")
                row["緯度"] = lat
            if lon is not None:
                RowSupport.append_text(row, "備考", f"原データ経度={raw_lon}")
                row["経度"] = lon


    # Check IDs after target-specific duplicate handling.
    ids = [r.get("ID", "") for r in out if r.get("ID")]
    dup_ids = [k for k, v in Counter(ids).items() if v > 1]
    if dup_ids:
        raise RuntimeError(f"{code}: duplicate normalized IDs remain: {dup_ids!r}")

    return {
        "code": code,
        "cfg": cfg,
        "source": src_path,
        "dest": dest,
        "encoding": enc,
        "rows": out,
    }


def main():
    schema = read_schema_fields(SCHEMA_PATH)
    if len(schema) != 39:
        raise RuntimeError(f"schema columns={len(schema)} expected=39")

    prepared = []
    for code, cfg in TARGETS.items():
        prepared.append(normalize_target(code, cfg, schema))

    print(f"preflight OK: {len(prepared)} municipalities")

    for item in prepared:
        StandardCsvWriter().write(item["dest"], schema, item["rows"])
        print(
            f"OK {item['code']} {item['cfg']['name']}: "
            f"rows={len(item['rows'])} encoding={item['encoding']}"
        )


if __name__ == "__main__":
    main()
