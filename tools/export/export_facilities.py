#!/usr/bin/env python3

import csv
import hashlib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CATALOG = ROOT / "catalog" / "datasets.csv"
PROVENANCE = ROOT / "catalog" / "normalized_sources.csv"
NORMALIZED = ROOT / "data" / "normalized"
OUT = ROOT / "dist" / "facilities-official.csv"

FIELDS = [
    "facility_id",
    "facility_category",
    "name",
    "prefecture_code",
    "prefecture_name",
    "municipality_code",
    "municipality_name",
    "address",
    "latitude",
    "longitude",
    "wheelchair_toilet",
    "multipurpose_toilet",
    "ostomate",
    "baby_bed",
    "baby_chair",
    "adult_bed",
    "nursing_space",
    "diaper_changing_space",
    "source_dataset_ids",
    "source_names",
    "source_urls",
    "licenses",
    "license_urls",
    "attributions",
    "source_normalized_path",
]


def clean(v):
    return (v or "").strip()


def yes_no(v):
    v = clean(v)

    if not v or v in {"unknown", "?"}:
        return ""

    if v in {
        "有", "あり", "有り", "○", "〇",
        "yes", "Yes", "YES", "true", "True", "1",
        "多目的トイレあり",
        "多機能トイレあり",
        "1（車椅子使用兼）",
        "1(男女共用トイレ)",
    }:
        return "yes"

    if v in {
        "無", "なし", "無し", "×", "✕",
        "no", "No", "NO", "false", "False", "0",
    }:
        return "no"

    return v


def count_to_yes_no(v):
    v = clean(v)

    if not v or v in {"unknown", "?"}:
        return ""

    mapped = yes_no(v)
    if mapped in {"yes", "no", ""}:
        return mapped

    try:
        n = float(v)
    except ValueError:
        return v

    return "yes" if n > 0 else "no"


def make_id(
    kind,
    path,
    dataset_ids,
    source_id,
    name,
    address,
    row_no,
):
    dataset_key = "|".join(sorted(dataset_ids))

    if source_id:
        material = "|".join([
            kind,
            dataset_key,
            source_id,
            name,
            address,
        ])
    else:
        material = "|".join([
            kind,
            dataset_key,
            path,
            str(row_no),
        ])

    digest = hashlib.sha1(
        material.encode("utf-8")
    ).hexdigest()[:16]

    return f"official-{digest}"


def load_catalog():
    with CATALOG.open(
        encoding="utf-8-sig",
        newline="",
    ) as f:
        rows = list(csv.DictReader(f))

    return {
        clean(r["dataset_id"]): r
        for r in rows
    }


def load_provenance():
    by_path = defaultdict(list)

    with PROVENANCE.open(
        encoding="utf-8-sig",
        newline="",
    ) as f:
        for r in csv.DictReader(f):
            by_path[clean(r["normalized_path"])].append(
                clean(r["dataset_id"])
            )

    return by_path


def provenance_fields(path, dataset_ids, catalog):
    rows = [catalog[x] for x in dataset_ids]

    def joined(field):
        values = []
        seen = set()

        for r in rows:
            value = clean(r.get(field))

            if value and value not in seen:
                values.append(value)
                seen.add(value)

        return "|".join(values)

    return {
        "source_dataset_ids": "|".join(dataset_ids),
        "source_names": joined("title"),
        "source_urls": joined("source_url"),
        "licenses": joined("license"),
        "license_urls": joined("license_url"),
        "attributions": joined("attribution"),
        "source_normalized_path": path,
    }


def export_public_toilet(path, dataset_ids, catalog):
    relpath = path.relative_to(ROOT).as_posix()
    prov = provenance_fields(
        relpath,
        dataset_ids,
        catalog,
    )

    pref_dir = path.parts[-4]
    mun_dir = path.parts[-3]

    path_pref_code, path_pref_name = pref_dir.split("-", 1)
    path_mun_code, path_mun_name = mun_dir.split("-", 1)

    with path.open(
        encoding="utf-8-sig",
        newline="",
    ) as f:
        reader = csv.DictReader(f)

        for row_no, r in enumerate(reader, 1):
            name = clean(r.get("名称"))
            lat = clean(r.get("緯度"))
            lon = clean(r.get("経度"))

            multi = clean(
                r.get("バリアフリートイレ数")
                or r.get("多機能トイレ数")
            )

            source_id = clean(r.get("ID"))
            address = clean(r.get("所在地_連結表記"))

            out = {
                "facility_id": make_id(
                    "public-toilet",
                    relpath,
                    dataset_ids,
                    source_id,
                    name,
                    address,
                    row_no,
                ),
                "facility_category": "public_toilet",
                "name": name,
                "prefecture_code": (
                    clean(r.get("所在地_全国地方公共団体コード"))[:2]
                    or path_pref_code
                ),
                "prefecture_name": (
                    clean(r.get("所在地_都道府県"))
                    or path_pref_name
                ),
                "municipality_code": (
                    clean(r.get("全国地方公共団体コード"))[:5]
                    or path_mun_code
                ),
                "municipality_name": (
                    clean(r.get("地方公共団体名"))
                    or path_mun_name
                ),
                "address": address,
                "latitude": lat,
                "longitude": lon,
                "wheelchair_toilet": yes_no(
                    r.get("車椅子使用者用トイレ有無")
                ),
                "multipurpose_toilet": count_to_yes_no(
                    multi
                ),
                "ostomate": yes_no(
                    r.get("オストメイト設置トイレ有無")
                ),
                "baby_bed": "",
                "baby_chair": "",
                "adult_bed": "",
                "nursing_space": "",
                "diaper_changing_space": yes_no(
                    r.get("乳幼児用設備設置トイレ有無")
                ),
            }

            out.update(prov)
            yield out


def export_barrier_free(path, dataset_ids, catalog):
    relpath = path.relative_to(ROOT).as_posix()
    prov = provenance_fields(
        relpath,
        dataset_ids,
        catalog,
    )

    with path.open(
        encoding="utf-8-sig",
        newline="",
    ) as f:
        reader = csv.DictReader(f)

        for row_no, r in enumerate(reader, 1):
            name = clean(
                r.get("facility_name")
                or r.get("formal_name")
            )
            lat = clean(r.get("latitude"))
            lon = clean(r.get("longitude"))

            source_id = clean(r.get("source_row"))
            address = clean(r.get("address"))

            out = {
                "facility_id": make_id(
                    "barrier-free",
                    relpath,
                    dataset_ids,
                    source_id,
                    name,
                    address,
                    row_no,
                ),
                "facility_category": "facility_with_toilet",
                "name": name,
                "prefecture_code": clean(
                    r.get("prefecture_code")
                ),
                "prefecture_name": clean(
                    r.get("prefecture_name")
                ),
                "municipality_code": clean(
                    r.get("municipality_code")
                ),
                "municipality_name": clean(
                    r.get("municipality_name")
                ),
                "address": address,
                "latitude": lat,
                "longitude": lon,
                "wheelchair_toilet": yes_no(
                    r.get("wheelchair_toilet")
                ),
                "multipurpose_toilet": yes_no(
                    r.get("multipurpose_toilet")
                ),
                "ostomate": yes_no(
                    r.get("ostomate")
                ),
                "baby_bed": yes_no(
                    r.get("baby_bed")
                ),
                "baby_chair": yes_no(
                    r.get("baby_chair")
                ),
                "adult_bed": yes_no(
                    r.get("adult_bed")
                ),
                "nursing_space": yes_no(
                    r.get("nursing_space")
                ),
                "diaper_changing_space": yes_no(
                    r.get("diaper_changing_space")
                ),
            }

            out.update(prov)
            yield out


def main():
    catalog = load_catalog()
    provenance = load_provenance()

    public_files = sorted(
        NORMALIZED.glob(
            "*-*/*/public-toilet/public-toilet.csv"
        )
    )
    barrier_files = sorted(
        NORMALIZED.glob(
            "*-*/barrier-free/*.csv"
        )
    )

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    total = 0
    public_count = 0
    barrier_count = 0

    with OUT.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()

        for path in public_files:
            relpath = path.relative_to(ROOT).as_posix()

            dataset_ids = provenance.get(relpath)
            if not dataset_ids:
                raise RuntimeError(
                    f"missing provenance: {relpath}"
                )

            for row in export_public_toilet(
                path,
                dataset_ids,
                catalog,
            ):
                writer.writerow(row)
                total += 1
                public_count += 1

        for path in barrier_files:
            relpath = path.relative_to(ROOT).as_posix()

            dataset_ids = provenance.get(relpath)
            if not dataset_ids:
                raise RuntimeError(
                    f"missing provenance: {relpath}"
                )

            for row in export_barrier_free(
                path,
                dataset_ids,
                catalog,
            ):
                writer.writerow(row)
                total += 1
                barrier_count += 1

    print("public-toilet:", public_count)
    print("barrier-free:", barrier_count)
    print("total:", total)
    print("output:", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
