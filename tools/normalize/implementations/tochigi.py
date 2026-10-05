import csv
import re
from pathlib import Path
from tools.normalize.core.normalization import RowSupport

COLUMNS = [
    "全国地方公共団体コード",
    "ID",
    "地方公共団体名",
    "名称",
    "名称_カナ",
    "名称_英語",
    "所在地_全国地方公共団体コード",
    "町字ID",
    "所在地_連結表記",
    "所在地_都道府県",
    "所在地_市区町村",
    "所在地_町字",
    "所在地_番地以下",
    "建物名等(方書)",
    "設置位置",
    "緯度",
    "経度",
    "高度の種別",
    "高度の値",
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
    "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無",
    "利用開始時間",
    "利用終了時間",
    "利用可能時間特記事項",
    "画像",
    "画像_ライセンス",
    "備考",
]

DIRECT_FIELDS = [
    "名称_カナ",
    "名称_英語",
    "設置位置",
    "緯度",
    "経度",
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
    "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無",
    "利用開始時間",
    "利用終了時間",
    "利用可能時間特記事項",
    "画像",
    "画像_ライセンス",
]

ROOT = Path(__file__).resolve().parents[3]

TARGETS = {
    "09208-小山市",
    "09211-矢板市",
}



def clean_name(value):
    return re.sub(r"\s+", " ", value or "").strip()


def empty_row():
    return {c: "" for c in COLUMNS}


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def normalize_oyama():
    src = ROOT / (
        "data/raw/09-栃木県/09208-小山市/"
        "public-toilet/public-toilet.csv"
    )
    dst = ROOT / (
        "data/normalized/09-栃木県/09208-小山市/"
        "public-toilet/public-toilet.csv"
    )

    with src.open(encoding="utf-8-sig", newline="") as f:
        source_rows = list(csv.DictReader(f))

    rows = []

    for r in source_rows:
        if not RowSupport.clean(r.get("名称")):
            continue

        out = empty_row()

        out["全国地方公共団体コード"] = RowSupport.clean(
            r.get("都道府県コード又は市区町村コード")
        )
        out["ID"] = RowSupport.clean(r.get("NO"))
        out["地方公共団体名"] = RowSupport.clean(r.get("市区町村名"))
        out["名称"] = clean_name(r.get("名称"))

        out["所在地_連結表記"] = RowSupport.clean(r.get("住所"))
        out["所在地_都道府県"] = RowSupport.clean(r.get("都道府県名"))
        out["所在地_市区町村"] = RowSupport.clean(r.get("市区町村名"))
        out["建物名等(方書)"] = RowSupport.clean(r.get("方書"))

        for field in DIRECT_FIELDS:
            out[field] = RowSupport.clean(r.get(field))

        # 原データの旧標準項目名を現行schemaへマップ
        out["バリアフリートイレ数"] = RowSupport.clean(
            r.get("多機能トイレ数")
        )

        out["備考"] = RowSupport.clean(r.get("備考"))
        rows.append(out)

    assert len(rows) == 115, len(rows)
    write_rows(dst, rows)
    return dst, len(rows)


def normalize_yaita():
    src = ROOT / (
        "data/raw/09-栃木県/09211-矢板市/"
        "public-toilet/public-toilet.csv"
    )
    dst = ROOT / (
        "data/normalized/09-栃木県/09211-矢板市/"
        "public-toilet/public-toilet.csv"
    )

    with src.open(encoding="cp932", newline="") as f:
        source_rows = list(csv.DictReader(f))

    rows = []

    for r in source_rows:
        if not RowSupport.clean(r.get("名称")):
            continue

        out = empty_row()

        out["全国地方公共団体コード"] = "092118"
        out["ID"] = ""
        out["地方公共団体名"] = "矢板市"
        out["名称"] = clean_name(r.get("名称"))

        out["所在地_連結表記"] = RowSupport.clean(r.get("住所"))
        out["所在地_都道府県"] = "栃木県"
        out["所在地_市区町村"] = "矢板市"
        out["建物名等(方書)"] = RowSupport.clean(r.get("方書"))

        for field in DIRECT_FIELDS:
            out[field] = RowSupport.clean(r.get(field))

        # 原データの旧標準項目名を現行schemaへマップ
        out["バリアフリートイレ数"] = RowSupport.clean(
            r.get("多機能トイレ数")
        )

        notes = []

        wheelchair_raw = RowSupport.clean(
            r.get("車椅子使用者用トイレ有無")
        )
        if wheelchair_raw not in {"", "有", "無"}:
            out["車椅子使用者用トイレ有無"] = ""
            notes.append(
                "原データ 車椅子使用者用トイレ有無: "
                + wheelchair_raw
            )

        if out["利用開始時間"] == "0:00":
            out["利用開始時間"] = "00:00"

        if RowSupport.clean(r.get("備考")):
            notes.append(RowSupport.clean(r.get("備考")))

        if RowSupport.clean(r.get("照会先")):
            notes.append("照会先: " + RowSupport.clean(r.get("照会先")))

        out["備考"] = " / ".join(notes)
        rows.append(out)

    assert len(rows) == 26, len(rows)
    write_rows(dst, rows)
    return dst, len(rows)


def main():
    normalizers = (
        ("09208-小山市", normalize_oyama),
        ("09211-矢板市", normalize_yaita),
    )

    for municipality, normalize in normalizers:
        if municipality not in TARGETS:
            continue

        path, count = normalize()
        print(f"{path.relative_to(ROOT)}: {count} rows")


if __name__ == "__main__":
    main()
