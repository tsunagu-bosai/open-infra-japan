#!/usr/bin/env python3

import csv
from pathlib import Path

from tools import normalize_public_toilet as common
from tools.normalize.core.municipality import six_digit_municipality_code
from tools.normalize.core.normalization import RowSupport

ROOT = Path(__file__).resolve().parents[3]

SOURCE = (
    ROOT
    / "data/raw/27-大阪府/27000-大阪府/public-toilet"
    / "270008_barrier_free_toilet.csv"
)

MASTER = ROOT / "data/reference/municipalities.csv"
CATALOG = ROOT / "catalog/datasets.csv"
SOURCE_DATASET_URL = "https://data.bodik.jp/dataset/270008_barrier_free_toilet"

FIELDS = [
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



def main():
    with MASTER.open(encoding="utf-8-sig", newline="") as f:
        master = list(csv.DictReader(f))

    name_to_row = {
        RowSupport.clean(r["municipality_name"]): r
        for r in master
        if r["prefecture_code"] == "27"
    }

    with CATALOG.open(encoding="utf-8-sig", newline="") as f:
        catalog_rows = list(csv.DictReader(f))

    # この府統合データを出典として、現在 published 扱いの自治体だけを
    # 自治体別の正規化出力へ分割する。調査時点の status には依存しない。
    targets = {
        RowSupport.clean(r["municipality_code"]): RowSupport.clean(r["municipality_name"])
        for r in catalog_rows
        if RowSupport.clean(r["prefecture_code"]) == "27"
        and RowSupport.clean(r["dataset_type"]) == "public-toilet"
        and RowSupport.clean(r["publication_status"]) == "published"
        and RowSupport.clean(r["source_url"]) == SOURCE_DATASET_URL
    }

    with SOURCE.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    outputs = {}

    for src in rows:
        municipality_name = RowSupport.clean(src["所在地_市区町村"])

        m = name_to_row.get(municipality_name)
        if not m:
            # 大阪市・堺市の区は既存catalogedなので今回対象外
            continue

        code5 = RowSupport.clean(m["municipality_code"])

        if code5 not in targets:
            continue

        # 全国自治体マスターの5桁コードから、元資料にある大阪府コードを
        # 流用せず自治体コードを設定する。
        code6 = six_digit_municipality_code(code5)

        out = {k: "" for k in FIELDS}

        for field in FIELDS:
            if field in src:
                out[field] = RowSupport.clean(src[field])

        out["全国地方公共団体コード"] = code6
        out["地方公共団体名"] = municipality_name
        out["所在地_全国地方公共団体コード"] = code6
        out["所在地_都道府県"] = "大阪府"
        out["所在地_市区町村"] = municipality_name


        outputs.setdefault((code5, municipality_name), []).append(out)

    total = 0

    for (code5, name), rows in sorted(outputs.items()):
        municipality_dir = f"{code5}-{name}"
        patches = common.load_patches("27-大阪府", municipality_dir)

        if patches:
            applied, problems = common.apply_patches(
                rows,
                patches,
                SOURCE,
            )
            if problems:
                raise RuntimeError(
                    f"{municipality_dir}: patch errors: "
                    + " | ".join(problems)
                )
            print(
                f"{code5} {name}: patches applied={applied}"
            )

        outdir = (
            ROOT
            / "data/normalized/27-大阪府"
            / municipality_dir
            / "public-toilet"
        )
        outdir.mkdir(parents=True, exist_ok=True)

        outfile = outdir / "public-toilet.csv"

        with outfile.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(
                f,
                fieldnames=FIELDS,
                lineterminator="\n",
            )
            w.writeheader()
            w.writerows(rows)

        print(f"{code5} {name}: {len(rows)}")
        total += len(rows)

    print()
    print("municipalities:", len(outputs))
    print("normalized rows:", total)


if __name__ == "__main__":
    main()
