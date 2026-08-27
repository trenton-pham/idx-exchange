import os
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

START_YEAR = 2024
CURR_YEAR = 2026
CURR_MONTH = 7
START_MONTH = 1
END_MONTH = 12

listing = []
sold = []

listing_count = []
sold_count = []

for year in range(START_YEAR, CURR_YEAR + 1):

    for month in range(START_MONTH, END_MONTH + 1):

        if year == CURR_YEAR and month > CURR_MONTH:
            break

        listing_file = RAW_DIR / f"CRMLSListing{year}{month:02d}.csv"

        if os.path.exists(listing_file):
            df_listing = pd.read_csv(listing_file, low_memory=False)

        else:
            continue

        filled_sold_file = RAW_DIR / f"CRMLSSold{year}{month:02d}_filled.csv"
        
        if os.path.exists(filled_sold_file):
            df_sold = pd.read_csv(filled_sold_file, low_memory=False)
        
        else:
            base_sold_file = RAW_DIR / f"CRMLSSold{year}{month:02d}.csv"
            if os.path.exists(base_sold_file):
                df_sold = pd.read_csv(base_sold_file, low_memory=False)

            else:
                continue

        listing.append(df_listing)
        listing_count.append(df_listing.shape[0])

        sold.append(df_sold)
        sold_count.append(df_sold.shape[0])

listing_comb = pd.concat(listing, ignore_index=True)
sold_comb = pd.concat(sold, ignore_index=True)

print(listing_comb.shape[0], sold_comb.shape[0])

"""
Confirmed row counts before filtering:
- Listings: 967777
- Sold: 665370
"""

listing_comb = listing_comb[listing_comb["PropertyType"] == "Residential"]
sold_comb = sold_comb[sold_comb["PropertyType"] == "Residential"]

listing_comb.to_csv(os.path.join(PROCESSED_DIR, "CRMLSListing_202401_202605.csv"), index=False)
sold_comb.to_csv(os.path.join(PROCESSED_DIR, "CRMLSSold_202401_202605.csv"), index=False)

print(listing_comb.shape[0], sold_comb.shape[0])

"""
Confirmed row counts after filtering for Residential property type:
- Listings: 616072
- Sold: 447964
"""