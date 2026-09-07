"""Combine available monthly CRMLS files into residential datasets."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

LISTING_PATTERN = re.compile(r"^CRMLSListing(\d{6})\.csv$")
SOLD_PATTERN = re.compile(r"^CRMLSSold(\d{6})\.csv$")
FILLED_SOLD_PATTERN = re.compile(r"^CRMLSSold(\d{6})_filled\.csv$")


@dataclass(frozen=True)
class MonthlyFiles:
    month: str
    listing: Path
    sold: Path


def _validate_month_key(value: str) -> None:
    year = int(value[:4])
    month = int(value[4:])
    if year < 1 or not 1 <= month <= 12:
        raise ValueError(f"Invalid YYYYMM value in raw filename: {value}")


def discover_monthly_files(raw_dir: Path = RAW_DIR) -> list[MonthlyFiles]:
    listings: dict[str, Path] = {}
    sold_files: dict[str, Path] = {}
    filled_sold_files: dict[str, Path] = {}

    for path in raw_dir.iterdir():
        if not path.is_file():
            continue
        for pattern, destination in (
            (LISTING_PATTERN, listings),
            (SOLD_PATTERN, sold_files),
            (FILLED_SOLD_PATTERN, filled_sold_files),
        ):
            match = pattern.fullmatch(path.name)
            if match:
                month = match.group(1)
                _validate_month_key(month)
                destination[month] = path
                break

    listing_months = set(listings)
    sold_months = set(sold_files) | set(filled_sold_files)
    missing_sold = sorted(listing_months - sold_months)
    missing_listings = sorted(sold_months - listing_months)
    if missing_sold or missing_listings:
        problems = []
        if missing_sold:
            problems.append("missing sold files for " + ", ".join(missing_sold))
        if missing_listings:
            problems.append(
                "missing listing files for " + ", ".join(missing_listings)
            )
        raise FileNotFoundError(
            "Incomplete monthly CRMLS data: " + "; ".join(problems)
        )
    if not listing_months:
        raise FileNotFoundError(f"No monthly CRMLS CSV files found in {raw_dir}.")

    monthly_files = []
    for month in sorted(listing_months):
        sold_path = filled_sold_files.get(month) or sold_files[month]
        monthly_files.append(MonthlyFiles(month, listings[month], sold_path))
    return monthly_files


def combine_monthly_data(
    raw_dir: Path = RAW_DIR, processed_dir: Path = PROCESSED_DIR
) -> tuple[int, int]:
    monthly_files = discover_monthly_files(raw_dir)
    listing_frames = [
        pd.read_csv(files.listing, low_memory=False) for files in monthly_files
    ]
    sold_frames = [pd.read_csv(files.sold, low_memory=False) for files in monthly_files]

    listing_combined = pd.concat(listing_frames, ignore_index=True)
    sold_combined = pd.concat(sold_frames, ignore_index=True)
    print(
        "Rows before Residential filter: "
        f"{len(listing_combined):,} listings, {len(sold_combined):,} sold."
    )

    for label, frame in (("listing", listing_combined), ("sold", sold_combined)):
        if "PropertyType" not in frame.columns:
            raise KeyError(
                f"{label.title()} data is missing required PropertyType column."
            )

    listing_combined = listing_combined[
        listing_combined["PropertyType"] == "Residential"
    ]
    sold_combined = sold_combined[sold_combined["PropertyType"] == "Residential"]

    processed_dir.mkdir(parents=True, exist_ok=True)
    listing_combined.to_csv(processed_dir / "CRMLSListing.csv", index=False)
    sold_combined.to_csv(processed_dir / "CRMLSSold.csv", index=False)
    print(
        "Rows after Residential filter: "
        f"{len(listing_combined):,} listings, {len(sold_combined):,} sold."
    )
    return len(listing_combined), len(sold_combined)


def main() -> int:
    combine_monthly_data()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
