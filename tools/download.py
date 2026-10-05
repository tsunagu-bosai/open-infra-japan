#!/usr/bin/env python3

import argparse
import csv
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATASETS = ROOT / "catalog" / "datasets.csv"
REFERENCE_MUNICIPALITIES = ROOT / "data" / "reference" / "municipalities.csv"
RAW_DIR = ROOT / "data" / "raw"


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def get_extension(row):
    fmt = (row.get("format") or "").strip().lower()

    extensions = {
        "csv": ".csv",
        "xlsx": ".xlsx",
        "xls": ".xls",
        "json": ".json",
        "geojson": ".geojson",
    }

    if fmt in extensions:
        return extensions[fmt]

    # format が不明な場合はURLから取得
    path = urllib.parse.urlparse(row["download_url"]).path
    suffix = Path(path).suffix

    return suffix or ".dat"


def get_filename(row):
    url = row["download_url"].strip()
    url_path = urllib.parse.urlparse(url).path
    filename = Path(url_path).name

    # URLから適切なファイル名が取れる場合はそのまま使用
    if filename and "." in filename:
        return filename

    return (
        f"{row['municipality_code']}_"
        f"{row['dataset_type']}"
        f"{get_extension(row)}"
    )



def validate_download(row, data, content_type):
    fmt = (row.get("format") or "").strip().lower()
    prefix = data[:512].lstrip().lower()
    content_type = (content_type or "").lower()

    if fmt == "xlsx":
        # XLSX is a ZIP container. HTML error/landing pages are a common false download.
        if not data.startswith(b"PK\x03\x04"):
            return False, f"expected xlsx/zip, got {content_type or 'unknown content-type'}"
    elif fmt == "csv":
        if prefix.startswith(b"<!doctype html") or prefix.startswith(b"<html"):
            return False, f"expected csv, got html ({content_type or 'unknown content-type'})"

    return True, ""

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--prefecture",
        help="都道府県コード（例: 13）",
    )

    parser.add_argument(
        "--dataset",
        help="データ種別（例: public-toilet）",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="既存ファイルを上書き",
    )

    args = parser.parse_args()

    datasets = read_csv(DATASETS)
    reference_municipalities = read_csv(REFERENCE_MUNICIPALITIES)

    reference_municipality_map = {
        row["municipality_code"].strip(): row
        for row in reference_municipalities
    }

    targets = []

    for row in datasets:
        if args.prefecture:
            if row["prefecture_code"].strip() != args.prefecture:
                continue

        if args.dataset:
            if row["dataset_type"].strip() != args.dataset:
                continue

        if not row["download_url"].strip():
            continue

        targets.append(row)

    print(f"Targets: {len(targets)}")

    downloaded = 0
    skipped = 0
    failed = 0

    for row in targets:
        publication_status = (
            row.get("publication_status") or "unknown"
        ).strip()

        if publication_status != "published":
            print(
                f"SKIP: {row['municipality_name']} "
                f"({publication_status})"
            )
            skipped += 1
            continue

        fmt = (row.get("format") or "").strip().lower()
        if fmt not in {"csv", "xlsx", "xls", "json", "geojson"}:
            print(
                f"SKIP: {row['municipality_name'] or row['prefecture_name']} "
                f"(unsupported format: {fmt or 'unknown'})"
            )
            skipped += 1
            continue

        code = row["municipality_code"].strip()
        reference_municipality = (
            reference_municipality_map.get(code) if code else None
        )

        if code and not reference_municipality:
            print(
                f"ERROR: municipality not found in reference: "
                f"{code} {row['municipality_name']}"
            )
            failed += 1
            continue

        prefecture_code = row["prefecture_code"].strip()
        if reference_municipality:
            reference_prefecture_code = (
                reference_municipality["prefecture_code"].strip()
            )
            if reference_prefecture_code != prefecture_code:
                print(
                    f"ERROR: prefecture code mismatch in reference: "
                    f"{code} catalog={prefecture_code} "
                    f"reference={reference_prefecture_code}"
                )
                failed += 1
                continue
            prefecture_name = (
                reference_municipality["prefecture_name"].strip()
            )
            scope_dir = (
                f"{code}-"
                f"{reference_municipality['municipality_name'].strip()}"
            )
        else:
            prefecture_name = row["prefecture_name"].strip()
            scope_dir = "prefecture"

        prefecture_dir = f"{prefecture_code}-{prefecture_name}"

        directory = (
            RAW_DIR
            / prefecture_dir
            / scope_dir
            / row["dataset_type"].strip()
        )

        directory.mkdir(parents=True, exist_ok=True)

        filename = get_filename(row)
        destination = directory / filename

        if destination.exists() and not args.overwrite:
            print(f"SKIP: {destination.relative_to(ROOT)}")
            skipped += 1
            continue

        url = row["download_url"].strip()

        target_name = row["municipality_name"] or row["prefecture_name"]
        print(f"GET : {target_name} -> {filename}")

        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent":
                        "OpenInfraJapan/0.1 "
                        "(open-data downloader)"
                },
            )

            with urllib.request.urlopen(
                request,
                timeout=30,
            ) as response:
                data = response.read()
                content_type = response.headers.get("Content-Type", "")

            valid, reason = validate_download(row, data, content_type)
            if not valid:
                print(f"FAIL: {url}")
                print(f"      invalid download: {reason}")
                failed += 1
                continue

            destination.write_bytes(data)

            print(
                f" OK : {destination.relative_to(ROOT)} "
                f"({len(data):,} bytes)"
            )

            downloaded += 1

        except Exception as e:
            print(f"FAIL: {url}")
            print(f"      {e}")
            failed += 1

    print()
    print(f"Downloaded: {downloaded}")
    print(f"Skipped:    {skipped}")
    print(f"Failed:     {failed}")



if __name__ == "__main__":
    main()
