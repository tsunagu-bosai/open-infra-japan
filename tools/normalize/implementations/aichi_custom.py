#!/usr/bin/env python3
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from tools.normalize.core.linkdata_xls import LinkDataXlsReader

try:
    import xlrd
except ImportError as exc:
    raise RuntimeError("xls処理に xlrd が必要です") from exc

from tools import normalize_public_toilet as common
from tools.normalize.core.normalization import (
    LenientEndOfDayTimeStrategy,
    RowSupport,
    StandardCsvWriter,
    ValueCleaner,
)
from tools.normalize.core.schema import read_schema_fields

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "schema/standard/public-toilet/schema.csv"
RAW = ROOT / "data/raw"
OUT = ROOT / "data/normalized"

TARGETS = {
    "23203": ("一宮市", "複数CSV統合"),
    "23210": ("刈谷市", "232106_public_toilet_20260401.csv"),
    "23226": ("尾張旭市", "232262_public_toilet.xls"),
}

PLACEHOLDERS = {"-", "ー", "－", "無し", "なし"}
CLEANER = ValueCleaner(PLACEHOLDERS)


def blank_row(fields: list[str]) -> dict[str, str]:
    return {k: "" for k in fields}



TIME_NORMALIZER = LenientEndOfDayTimeStrategy(cleaner=CLEANER)



def read_csv_rows(path: Path, encoding: str):
    with path.open("r", encoding=encoding, newline="") as f:
        return list(csv.DictReader(f))



def apply_patches(pref_dir: str, muni_dir: str, rows, source: Path) -> int:
    patches = common.load_patches(pref_dir, muni_dir)
    applied, problems = common.apply_patches(rows, patches, source)
    if problems:
        raise RuntimeError(
            f"{muni_dir}: patch適用失敗: " + " | ".join(map(str, problems))
        )
    return applied


def output_path(pref_dir: str, muni_dir: str) -> Path:
    return OUT / pref_dir / muni_dir / "public-toilet/public-toilet.csv"


def apply_patches_with_materialized_id_changes(
    pref_dir: str,
    muni_dir: str,
    rows,
    source: Path,
) -> int:
    # ID変更patchのうち、重複raw IDを一意化するためnormalizer側で
    # すでに -2/-3 を付与済みのものだけ、関係を検証して既反映扱いにする。
    patches = common.load_patches(pref_dir, muni_dir)
    row_ids = {(row.get("ID") or "").strip() for row in rows}

    remaining = []
    materialized = 0

    for patch in patches:
        field = (patch.get("field") or "").strip()
        # load_patches() 側のpatch IDキーは "id"。
        # 既存/将来の互換性のため "ID" も受ける。
        selector = (patch.get("id") or patch.get("ID") or "").strip()
        original = (patch.get("original_value") or "").strip()
        new_value = (patch.get("new_value") or "").strip()

        if (
            field == "ID"
            and selector in row_ids
            and original
            and selector.startswith(original + "-")
            and (not new_value or new_value == selector)
        ):
            materialized += 1
            continue

        remaining.append(patch)

    applied, problems = common.apply_patches(rows, remaining, source)
    if problems:
        raise RuntimeError(
            f"{muni_dir}: patch適用失敗: " + " | ".join(map(str, problems))
        )

    return applied + materialized


def address_with_pref(address: str, pref: str) -> str:
    address = CLEANER(address, preserve_placeholder=True)
    if not address:
        return ""
    if address.startswith(pref):
        return address
    return pref + address


def ichinomiya_key_name_addr(r):
    return (
        CLEANER(r.get("ITEM005") or r.get("施設名称"), preserve_placeholder=True),
        CLEANER(r.get("ITEM008") or r.get("所在地"), preserve_placeholder=True),
    )


def ichinomiya_key_coord(r):
    x = CLEANER(r.get("X") or r.get("Ｘ"), preserve_placeholder=True)
    y = CLEANER(r.get("Y") or r.get("Ｙ"), preserve_placeholder=True)
    try:
        return (round(float(x), 6), round(float(y), 6))
    except Exception:
        return ("", "")


def ichinomiya_from_item(fields, r, prefix: str, source_label: str):
    row = blank_row(fields)
    uid = CLEANER(r.get("UserID"), preserve_placeholder=True)
    code6 = "232033"
    address = CLEANER(r.get("ITEM008"), preserve_placeholder=True)

    row["全国地方公共団体コード"] = code6
    row["ID"] = f"23203-{prefix}-{int(uid):06d}"
    row["地方公共団体名"] = "愛知県一宮市"
    row["名称"] = CLEANER(r.get("ITEM005"), preserve_placeholder=True)
    row["名称_カナ"] = CLEANER(r.get("ITEM006"), preserve_placeholder=True)
    english_name = CLEANER(r.get("ITEM007"), preserve_placeholder=True)
    # 原本の複数行英語名称に行末空白が含まれるため、改行は保持しつつ除去する。
    row["名称_英語"] = "\n".join(line.rstrip() for line in english_name.splitlines())
    row["所在地_全国地方公共団体コード"] = code6
    row["所在地_連結表記"] = address_with_pref(address, "愛知県")
    row["所在地_都道府県"] = "愛知県"
    row["所在地_市区町村"] = "一宮市"
    row["建物名等(方書)"] = CLEANER(r.get("ITEM009"), preserve_placeholder=True)
    row["設置位置"] = CLEANER(r.get("ITEM012"), preserve_placeholder=True)
    row["緯度"] = CLEANER(r.get("Y"), preserve_placeholder=True)
    row["経度"] = CLEANER(r.get("X"), preserve_placeholder=True)
    row["車椅子使用者用トイレ有無"] = CLEANER(r.get("ITEM014"))
    row["乳幼児用設備設置トイレ有無"] = CLEANER(r.get("ITEM015"))
    row["オストメイト設置トイレ有無"] = CLEANER(r.get("ITEM016"))
    row["利用開始時間"] = TIME_NORMALIZER(r.get("ITEM020"))
    row["利用終了時間"] = TIME_NORMALIZER(r.get("ITEM021"))

    time_note = CLEANER(r.get("ITEM022"), preserve_placeholder=True)
    closed = CLEANER(r.get("ITEM023"))
    notes = []
    if time_note:
        notes.append("利用時間補足：" + time_note)
    if closed:
        notes.append("休所日：" + closed)
    row["利用可能時間特記事項"] = " / ".join(notes)

    note_parts = [f"原本：{source_label}、UserID={uid}"]
    multi = CLEANER(r.get("ITEM010"), preserve_placeholder=True)
    multi_type = CLEANER(r.get("ITEM011"), preserve_placeholder=True)
    phone_raw = CLEANER(r.get("ITEM013"), preserve_placeholder=True)
    # 一宮市原本では「無し」と「なし」が混在する。
    # 従来CSVで明示的に保持していた「なし」は残し、
    # 「無し」は欠損相当として従来どおり空扱いにする。
    phone = phone_raw if phone_raw == "なし" else CLEANER(r.get("ITEM013"))
    universal = CLEANER(r.get("ITEM017"), preserve_placeholder=True)
    source_note = CLEANER(r.get("ITEM024"))
    if multi:
        note_parts.append(f"多目的トイレ数：{multi}")
    if multi_type:
        note_parts.append(f"多目的トイレ種別：{multi_type}")
    if phone:
        note_parts.append(f"電話番号：{phone}")
    if universal:
        note_parts.append(f"ユニバーサルシート有無：{universal}")
    if source_note:
        note_parts.append(f"原本備考：{source_note}")
    row["備考"] = "；".join(note_parts)
    return row


def normalize_ichinomiya(fields: list[str]):
    pref_dir, muni_dir = "23-愛知県", "23203-一宮市"
    rdir = RAW / pref_dir / muni_dir / "public-toilet"
    wheel_path = rdir / "kurumaisutaioutoire.csv"
    infant_path = rdir / "nyuuyoujitaioutoire.csv"
    ost_path = rdir / "ostomate.csv"
    uni_path = rdir / "universalsheet.csv"

    wheel = read_csv_rows(wheel_path, "cp932")
    infant = read_csv_rows(infant_path, "cp932")
    ost = read_csv_rows(ost_path, "cp932")
    uni = read_csv_rows(uni_path, "cp932")

    rows = [ichinomiya_from_item(fields, r, "W", "車椅子対応一覧") for r in wheel]

    by_name_addr = defaultdict(list)
    by_coord = defaultdict(list)
    for i, r in enumerate(wheel):
        by_name_addr[ichinomiya_key_name_addr(r)].append(i)
        by_coord[ichinomiya_key_coord(r)].append(i)

    unmatched_infant = []
    for r in infant:
        # 乳幼児一覧は名称+所在地の完全一致だけを同一施設とみなす。
        # 座標だけ一致する1件は既存データ上は別施設として追加される。
        matches = by_name_addr.get(ichinomiya_key_name_addr(r), [])
        if len(matches) == 1:
            idx = matches[0]
            rows[idx]["乳幼児用設備設置トイレ有無"] = "有"
        elif len(matches) == 0:
            unmatched_infant.append(r)
        else:
            raise RuntimeError(
                f"23203 一宮市: 乳幼児一覧の照合が複数候補: "
                f"{CLEANER(r.get('ITEM005'), preserve_placeholder=True)!r}"
            )

    if len(unmatched_infant) != 1:
        raise RuntimeError(
            f"23203 一宮市 unmatched infant={len(unmatched_infant)} expected=1"
        )
    rows.append(
        ichinomiya_from_item(
            fields, unmatched_infant[0], "I", "乳幼児対応一覧"
        )
    )

    # 補助一覧は基礎データとの整合確認に使う。
    for source_rows, field, label in (
        (ost, "オストメイト設置トイレ有無", "オストメイト一覧"),
        (uni, None, "ユニバーサルシート一覧"),
    ):
        for r in source_rows:
            matches = by_name_addr.get(ichinomiya_key_name_addr(r), [])
            if not matches:
                matches = by_coord.get(ichinomiya_key_coord(r), [])
            if len(matches) != 1:
                raise RuntimeError(
                    f"23203 一宮市: {label}照合失敗 "
                    f"{CLEANER(r.get('施設名称'), preserve_placeholder=True)!r}"
                )
            if field:
                rows[matches[0]][field] = "有"

    # 一宮市には現時点で専用patchなし。共通関数で将来追加にも対応。
    applied = apply_patches(pref_dir, muni_dir, rows, wheel_path)
    return pref_dir, muni_dir, wheel_path, rows, applied


def normalize_legacy_like(fields, r, *, code6, pref_name, city_name,
                          id_value, localgov_name, address_value,
                          multi_value="", time_note_field="利用可能時間特記事項",
                          normalize_times=True):
    row = blank_row(fields)
    mapping = [
        "名称", "名称_カナ", "名称_英語", "設置位置", "緯度", "経度",
        "男性トイレ総数", "男性トイレ数（小便器）",
        "男性トイレ数（和式）", "男性トイレ数（洋式）",
        "女性トイレ総数", "女性トイレ数（和式）",
        "女性トイレ数（洋式）", "男女共用トイレ総数",
        "男女共用トイレ数（和式）", "男女共用トイレ数（洋式）",
        "車椅子使用者用トイレ有無", "乳幼児用設備設置トイレ有無",
        "オストメイト設置トイレ有無", "画像", "画像_ライセンス", "備考",
    ]
    for field in mapping:
        row[field] = CLEANER(r.get(field), preserve_placeholder=True)

    row["全国地方公共団体コード"] = code6
    row["ID"] = id_value
    row["地方公共団体名"] = localgov_name
    row["所在地_全国地方公共団体コード"] = code6
    row["所在地_連結表記"] = address_value
    row["所在地_都道府県"] = pref_name
    row["所在地_市区町村"] = city_name
    row["建物名等(方書)"] = CLEANER(r.get("方書"), preserve_placeholder=True)
    if normalize_times:
        row["利用開始時間"] = TIME_NORMALIZER(r.get("利用開始時間"))
        row["利用終了時間"] = TIME_NORMALIZER(r.get("利用終了時間"))
    else:
        # patch の original_value と照合できるよう、patch適用前は原値を保持。
        row["利用開始時間"] = CLEANER(r.get("利用開始時間"), preserve_placeholder=True)
        row["利用終了時間"] = CLEANER(r.get("利用終了時間"), preserve_placeholder=True)
    row["利用可能時間特記事項"] = CLEANER(
        r.get(time_note_field), preserve_placeholder=True
    )

    if multi_value:
        RowSupport.append_note(row, f"多機能トイレ数:{multi_value}")
    return row


def normalize_kariya(fields: list[str]):
    pref_dir, muni_dir = "23-愛知県", "23210-刈谷市"
    source = RAW / pref_dir / muni_dir / "public-toilet/232106_public_toilet_20260401.csv"
    src = read_csv_rows(source, "utf-8-sig")
    rows = []
    seen = defaultdict(int)

    for r in src:
        no = CLEANER(r.get("NO"), preserve_placeholder=True)
        if not no:
            continue
        seen[no] += 1
        ident = no if seen[no] == 1 else f"{no}-{seen[no]}"
        address = CLEANER(r.get("住所"), preserve_placeholder=True)
        row = normalize_legacy_like(
            fields, r,
            code6="232106",
            pref_name="愛知県",
            city_name="刈谷市",
            id_value=ident,
            localgov_name="刈谷市",
            address_value=address,
            multi_value=CLEANER(r.get("多機能トイレ数"), preserve_placeholder=True),
            normalize_times=False,
        )
        rows.append(row)

    applied = apply_patches_with_materialized_id_changes(
        pref_dir, muni_dir, rows, source
    )
    return pref_dir, muni_dir, source, rows, applied

def normalize_owariasahi(fields: list[str]):
    pref_dir, muni_dir = "23-愛知県", "23226-尾張旭市"
    source = RAW / pref_dir / muni_dir / "public-toilet/232262_public_toilet.xls"
    src = LinkDataXlsReader().read(source)
    rows = []

    for r in src:
        no = CLEANER(r.get("ＮＯ"), preserve_placeholder=True)
        if not no:
            continue
        address = CLEANER(r.get("住所"), preserve_placeholder=True)
        row = normalize_legacy_like(
            fields, r,
            code6="232262",
            pref_name="愛知県",
            city_name="尾張旭市",
            id_value=no,
            localgov_name="尾張旭市",
            address_value=address,
            multi_value=CLEANER(r.get("多機能トイレ数"), preserve_placeholder=True),
            time_note_field="利用可能日時特記事項",
            normalize_times=False,
        )
        rows.append(row)

    applied = apply_patches(pref_dir, muni_dir, rows, source)
    return pref_dir, muni_dir, source, rows, applied


def main():
    fields = read_schema_fields(SCHEMA)
    if len(fields) != 39:
        raise RuntimeError(f"schema columns={len(fields)} expected=39")

    dispatch = {
        "23203": normalize_ichinomiya,
        "23210": normalize_kariya,
        "23226": normalize_owariasahi,
    }

    prepared = []
    for code in TARGETS:
        prepared.append((code, dispatch[code](fields)))

    print(f"preflight OK: {len(prepared)} municipalities")

    for code, (pref_dir, muni_dir, source, rows, applied) in prepared:
        dest = output_path(pref_dir, muni_dir)
        StandardCsvWriter().write(dest, fields, rows)
        print(
            f"OK {muni_dir}: rows={len(rows)} "
            f"source={source.name} patches={applied}"
        )


if __name__ == "__main__":
    main()
