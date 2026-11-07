from __future__ import annotations

import csv
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.normalize.core import runner


class CoordinateSupplementsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.relative = "data/normalized/01-北海道/01202-函館市/public-toilet/public-toilet.csv"
        self.output_dir = self.root / "data/normalized/01-北海道"
        self.csv_path = self.root / self.relative
        self.csv_path.parent.mkdir(parents=True)
        self.ledger_path = self.root / "catalog/public_toilet_coordinate_supplements.csv"
        self.ledger_path.parent.mkdir(parents=True)
        self.entry = {
            "normalized_path": self.relative,
            "row_number": "1",
            "source_id": "pt-1",
            "prefecture_code": "01",
            "municipality_code": "01202",
            "facility_name": "公園トイレ",
            "source_address": "北海道函館市元町1-1",
            "latitude": "41.765000",
            "longitude": "140.700000",
        }
        with self.ledger_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.entry, lineterminator="\n")
            writer.writeheader()
            writer.writerow(self.entry)
        self.fields = ["ID", "名称", "所在地_連結表記", "緯度", "経度"]
        self.write_row("", "")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_row(self, latitude: str, longitude: str) -> None:
        with self.csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.fields, lineterminator="\n")
            writer.writeheader()
            writer.writerow({
                "ID": self.entry["source_id"],
                "名称": self.entry["facility_name"],
                "所在地_連結表記": self.entry["source_address"],
                "緯度": latitude,
                "経度": longitude,
            })

    def apply(self) -> int:
        with patch.object(runner, "REPO_ROOT", self.root):
            return runner.apply_coordinate_supplements(self.output_dir, "01")

    def sha256(self) -> str:
        return hashlib.sha256(self.csv_path.read_bytes()).hexdigest()

    def test_first_apply_and_identical_second_apply_are_idempotent(self) -> None:
        self.assertEqual(self.apply(), 1)
        first_hash = self.sha256()
        self.assertEqual(self.apply(), 1)
        self.assertEqual(self.sha256(), first_hash)

    def test_source_id_survives_row_reordering(self) -> None:
        with self.csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.fields, lineterminator="\n")
            writer.writeheader()
            writer.writerow({"ID": "other", "名称": "別施設", "所在地_連結表記": "別住所", "緯度": "", "経度": ""})
            writer.writerow({
                "ID": self.entry["source_id"],
                "名称": self.entry["facility_name"],
                "所在地_連結表記": self.entry["source_address"],
                "緯度": "",
                "経度": "",
            })
        self.assertEqual(self.apply(), 1)
        with self.csv_path.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[1]["緯度"], self.entry["latitude"])
        self.assertEqual(rows[1]["経度"], self.entry["longitude"])

    def test_different_existing_coordinates_are_not_overwritten(self) -> None:
        self.write_row("41.765001", "140.700000")
        before = self.sha256()
        with self.assertRaisesRegex(RuntimeError, "coordinate mismatch"):
            self.apply()
        self.assertEqual(self.sha256(), before)

    def test_one_sided_coordinates_are_rejected_without_modification(self) -> None:
        self.write_row("41.765000", "")
        before = self.sha256()
        with self.assertRaisesRegex(RuntimeError, "one-sided coordinates"):
            self.apply()
        self.assertEqual(self.sha256(), before)

    def test_row_identity_mismatch_is_rejected(self) -> None:
        with self.csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.fields, lineterminator="\n")
            writer.writeheader()
            writer.writerow({"ID": "other", "名称": "別施設", "所在地_連結表記": "別住所", "緯度": "", "経度": ""})
        with self.assertRaisesRegex(RuntimeError, "address mismatch"):
            self.apply()


if __name__ == "__main__":
    unittest.main()
