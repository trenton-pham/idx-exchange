from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from process import combine_monthly_data, discover_monthly_files


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["ListingKey", "PropertyType"])
        writer.writeheader()
        writer.writerows(rows)


class ProcessTests(unittest.TestCase):
    def test_discovers_new_months_and_prefers_filled_sold_file(self):
        with tempfile.TemporaryDirectory() as directory:
            raw_dir = Path(directory)
            write_csv(
                raw_dir / "CRMLSListing202607.csv",
                [{"ListingKey": "l7", "PropertyType": "Residential"}],
            )
            write_csv(
                raw_dir / "CRMLSSold202607.csv",
                [{"ListingKey": "base", "PropertyType": "Residential"}],
            )
            write_csv(
                raw_dir / "CRMLSSold202607_filled.csv",
                [{"ListingKey": "filled", "PropertyType": "Residential"}],
            )
            write_csv(
                raw_dir / "CRMLSListing202608.csv",
                [{"ListingKey": "l8", "PropertyType": "Residential"}],
            )
            write_csv(
                raw_dir / "CRMLSSold202608.csv",
                [{"ListingKey": "s8", "PropertyType": "Residential"}],
            )

            discovered = discover_monthly_files(raw_dir)

        self.assertEqual([item.month for item in discovered], ["202607", "202608"])
        self.assertEqual(discovered[0].sold.name, "CRMLSSold202607_filled.csv")

    def test_incomplete_month_pair_fails_loudly(self):
        with tempfile.TemporaryDirectory() as directory:
            raw_dir = Path(directory)
            write_csv(
                raw_dir / "CRMLSListing202608.csv",
                [{"ListingKey": "l8", "PropertyType": "Residential"}],
            )
            with self.assertRaisesRegex(
                FileNotFoundError, "missing sold files for 202608"
            ):
                discover_monthly_files(raw_dir)

    def test_combines_all_discovered_months_and_filters_residential(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_dir = root / "raw"
            processed_dir = root / "processed"
            raw_dir.mkdir()
            write_csv(
                raw_dir / "CRMLSListing202607.csv",
                [
                    {"ListingKey": "l7", "PropertyType": "Residential"},
                    {"ListingKey": "other", "PropertyType": "Land"},
                ],
            )
            write_csv(
                raw_dir / "CRMLSSold202607.csv",
                [{"ListingKey": "base", "PropertyType": "Residential"}],
            )
            write_csv(
                raw_dir / "CRMLSSold202607_filled.csv",
                [{"ListingKey": "filled", "PropertyType": "Residential"}],
            )
            write_csv(
                raw_dir / "CRMLSListing202608.csv",
                [{"ListingKey": "l8", "PropertyType": "Residential"}],
            )
            write_csv(
                raw_dir / "CRMLSSold202608.csv",
                [{"ListingKey": "s8", "PropertyType": "Land"}],
            )

            counts = combine_monthly_data(raw_dir, processed_dir)
            listings = pd.read_csv(processed_dir / "CRMLSListing.csv")
            sold = pd.read_csv(processed_dir / "CRMLSSold.csv")

        self.assertEqual(counts, (2, 1))
        self.assertEqual(listings["ListingKey"].tolist(), ["l7", "l8"])
        self.assertEqual(sold["ListingKey"].tolist(), ["filled"])


if __name__ == "__main__":
    unittest.main()
