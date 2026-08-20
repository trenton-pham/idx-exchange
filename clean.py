from pathlib import Path
import os

import pandas as pd
import geopandas as gpd


listing_path = Path("data/mortgage/CRMLSListing_202401_202605_with_mortgage.csv")
sold_path = Path("data/mortgage/CRMLSSold_202401_202605_with_mortgage.csv")

output_dir = Path("data/cleaned")

listing = pd.read_csv(listing_path, low_memory=False)
sold = pd.read_csv(sold_path, low_memory=False)

# Removing duplicate columns created by mortgage_fetch.py
def clean_duplicate_columns(df):
    columns = df.columns
    for column in columns:
        if column.endswith(".1"):
            df.drop(column, axis=1, inplace=True)
    return df

listing = clean_duplicate_columns(listing)

# Convert date columns into datetime format
def to_datetime(df, date_columns): 
    df[date_columns] = df[date_columns].apply(pd.to_datetime, errors="coerce")
    return df


listing_date_columns = ["ListingContractDate", "ContractStatusChangeDate"]
sold_date_columns = [
        "ListingContractDate",
        "PurchaseContractDate",
        "CloseDate",
        "ContractStatusChangeDate",
    ]

listing = to_datetime(listing, listing_date_columns)
sold = to_datetime(sold, sold_date_columns)

sold["listing_after_close_flag"] = sold["ListingContractDate"] > sold["CloseDate"]
sold["purchase_after_close_flag"] = sold["PurchaseContractDate"] > sold["CloseDate"]
sold["negative_timeline_flag"] = sold["ListingContractDate"] > sold["PurchaseContractDate"]

timeline_flag_columns = [
    "listing_after_close_flag",
    "purchase_after_close_flag",
    "negative_timeline_flag",
]

print(sold[timeline_flag_columns].sum())
"""
Flag row count summary:
listing_after_close_flag      67
purchase_after_close_flag    239
negative_timeline_flag       290
"""

# Dropping redundant listing agent columns
def list_agent(df):
    columns = ["ListAgentEmail", "ListAgentFirstName", "ListAgentLastName"]
    df.drop(columns=columns, inplace=True)
    return df

listing = list_agent(listing)
sold = list_agent(sold)

# Filtering coordinates to California (note: may change to using zip-code or state data)

# Filter to California properties
listing = listing[listing["StateOrProvince"] == "CA"]
sold = sold[sold["StateOrProvince"] == "CA"]

# Normalizing coordinates to negative due to normalizing error (flipping signs)
listing["Longitude"] = listing["Longitude"].apply(lambda x: -x if x > 0 else x) 
sold["Longitude"] = sold["Longitude"].apply(lambda x: -x if x > 0 else x)

city_path = Path("data/city_boundaries/City_and_County_Boundaries.geojson")
city_gdf = gpd.read_file(city_path)
city_gdf = city_gdf.set_crs("EPSG:4326")

california_boundary = city_gdf.dissolve()

def flag_coordinates(df):
    df = df.dropna(subset=["Latitude", "Longitude"])
    
    df_points = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["Longitude"], df["Latitude"]),
        crs="EPSG:4326",
    )

    df = gpd.sjoin(
            df_points,
            california_boundary[["geometry"]],
            how="inner",
            predicate="within",
        )

    df["coordinates_in_california"] = (
        df["Latitude"].notna()
        & df["Longitude"].notna()
        & df["index_right"].notna()
    )

    return pd.DataFrame(df.drop(columns=["geometry", "index_right"]))

listing = flag_coordinates(listing)
sold = flag_coordinates(sold)

# Filtering values that aren't possible
def filter_nono_values(df, columns):
    for column in columns:
        df = df[df[column] >= 0]
    return df

listing_columns = ["DaysOnMarket", "BedroomsTotal", 
               "BathroomsTotalInteger"]

sold_columns = listing_columns + ["ClosePrice"]

listing = filter_nono_values(listing, listing_columns)
sold = filter_nono_values(sold, sold_columns)

# Filtering out properties with LivingArea less than 80 sqft
listing = listing[listing["LivingArea"] > 80]
sold = sold[sold["LivingArea"] > 80]

"""
Dropping redundant columns
- PropertyType: Assumed to be `Residential`
- MlsStatus: Constant `Closed` value
- ListingKey: Redundant with `ListingKeyNumeric`
"""
sold.drop(columns=["PropertyType", "MlsStatus", "ListingKey", 
                   "BuyerAgencyCompensationType", "OriginatingSystemName", 
                   "OriginatingSystemSubName", "AttachedGarageYN",
                   "FireplaceYN"], inplace=True)

# Filter zip codes to California
def filter_zip_codes(df):
    postal_code = df["PostalCode"].astype("string").str.strip()

    # Accept either 12345 or 12345-6789 and extract the base ZIP.
    zip5 = postal_code.str.extract(
        r"^(\d{5})(?:-\d{4})?$",
        expand=False,
    )

    zip_number = pd.to_numeric(zip5, errors="coerce")
    valid_zip = zip_number.between(90001, 96162)

    df = df.loc[valid_zip].copy()
    df["PostalCode"] = zip5.loc[valid_zip]

    return df

listing = filter_zip_codes(listing)
sold = filter_zip_codes(sold)

# Remove NaN cities
def remove_nan_cities(df):
    df = df[df["City"].notna()]
    return df

listing = remove_nan_cities(listing)
sold = remove_nan_cities(sold)

listing.to_csv(os.path.join(output_dir, "CRMLSListing_cleaned.csv"), index=False)
sold.to_csv(os.path.join(output_dir, "CRMLSSold_cleaned.csv"), index=False)