from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely


LISTING_PATH = Path("data/mortgage/CRMLSListing_with_mortgage.csv")
SOLD_PATH = Path("data/mortgage/CRMLSSold_with_mortgage.csv")
OUTPUT_DIR = Path("data/cleaned")
ZIP_CODE_PATH = Path("data/zip/california_valid_zip_codes.csv")
COUNTY_BOUNDARY_PATH = Path(
    "data/city_boundaries/City_and_County_Boundaries.geojson"
)
GEOGRAPHIC_CRS = "EPSG:4326"


# Removing duplicate columns created by mortgage_fetch.py
def clean_duplicate_columns(df):
    duplicate_columns = [column for column in df.columns if column.endswith(".1")]
    df.drop(columns=duplicate_columns, inplace=True)
    return df


# Convert date columns into datetime format
def to_datetime(df, date_columns):
    df[date_columns] = df[date_columns].apply(pd.to_datetime, errors="coerce")
    return df


# Dropping redundant listing agent columns
def list_agent_drop(df):
    columns = ["ListAgentEmail", "ListAgentFirstName", "ListAgentLastName"]
    df.drop(columns=columns, inplace=True, errors="ignore")
    return df


def filter_zip_codes(df, valid_zip_codes, *, retain_unmapped=False):
    postal_code = df["PostalCode"].astype("string").str.strip()

    # Handles 12345 and 12345-6789.
    zip5 = postal_code.str.extract(
        r"^(\d{5})(?:-\d{4})?$",
        expand=False,
    )

    valid = zip5.isin(valid_zip_codes)
    if retain_unmapped:
        df = df.copy()
        df["PostalCode"] = zip5.where(valid)
        return df
    df = df.loc[valid].copy()
    df["PostalCode"] = zip5.loc[valid]
    return df


def normalize_geographic_names(values):
    """Normalize names for exact, case-insensitive geographic comparisons."""
    return (
        values.astype("string")
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.casefold()
    )


def load_county_boundaries(path=COUNTY_BOUNDARY_PATH):
    """Load and combine the source polygons into one valid shape per county."""
    boundaries = gpd.read_file(path)
    if "COUNTY_NAME" not in boundaries.columns:
        raise ValueError(f"County boundary file is missing COUNTY_NAME: {path}")

    if boundaries.crs is None:
        boundaries = boundaries.set_crs(GEOGRAPHIC_CRS)
    else:
        boundaries = boundaries.to_crs(GEOGRAPHIC_CRS)

    boundaries = boundaries.loc[
        boundaries["COUNTY_NAME"].notna()
        & boundaries.geometry.notna()
        & ~boundaries.geometry.is_empty,
        ["COUNTY_NAME", "geometry"],
    ].copy()
    boundaries.geometry = boundaries.geometry.make_valid()
    county_boundaries = boundaries.dissolve(by="COUNTY_NAME", as_index=False)

    if county_boundaries.empty:
        raise ValueError(f"County boundary file contains no usable polygons: {path}")

    return county_boundaries[["COUNTY_NAME", "geometry"]]


def flag_coordinates(df, county_boundaries):
    """Flag coordinates that do not match their reported California county."""
    result = df.copy()

    latitude = pd.to_numeric(result["Latitude"], errors="coerce")
    longitude = pd.to_numeric(result["Longitude"], errors="coerce")

    # CRMLS occasionally supplies California longitudes with the wrong sign.
    longitude = longitude.mask(longitude > 0, -longitude)
    result["Latitude"] = latitude
    result["Longitude"] = longitude

    valid_coordinates = (
        latitude.notna()
        & longitude.notna()
        & latitude.between(-90, 90, inclusive="both")
        & longitude.between(-180, 180, inclusive="both")
    )

    coordinates_in_california = np.zeros(len(result), dtype=bool)
    coordinates_outside_county = np.ones(len(result), dtype=bool)

    if valid_coordinates.any():
        valid_positions = np.flatnonzero(valid_coordinates.to_numpy())
        points = shapely.points(
            longitude.iloc[valid_positions].to_numpy(),
            latitude.iloc[valid_positions].to_numpy(),
        )

        boundary_names = normalize_geographic_names(
            county_boundaries["COUNTY_NAME"]
        )
        geometries_by_county = {}
        all_geometries = []
        for county_name, geometry in zip(
            boundary_names, county_boundaries.geometry
        ):
            if pd.isna(county_name) or geometry is None or geometry.is_empty:
                continue
            geometries_by_county.setdefault(county_name, []).append(geometry)
            all_geometries.append(geometry)

        if all_geometries:
            county_names = list(geometries_by_county)
            county_geometries = np.empty(len(county_names), dtype=object)
            for position, county_name in enumerate(county_names):
                geometries = geometries_by_county[county_name]
                county_geometries[position] = (
                    geometries[0]
                    if len(geometries) == 1
                    else shapely.union_all(geometries)
                )

            # Preparing each county makes the repeated point-in-polygon checks
            # substantially faster than joining every point against every county.
            shapely.prepare(county_geometries)
            county_lookup = {
                county_name: position
                for position, county_name in enumerate(county_names)
            }
            reported_counties = normalize_geographic_names(
                result["CountyOrParish"]
            ).iloc[valid_positions]
            expected_county_positions = (
                reported_counties.map(county_lookup)
                .fillna(-1)
                .to_numpy(dtype=np.int64)
            )

            county_matches = np.zeros(len(valid_positions), dtype=bool)
            known_counties = expected_county_positions >= 0
            county_matches[known_counties] = shapely.intersects(
                county_geometries[expected_county_positions[known_counties]],
                points[known_counties],
            )

            coordinates_in_california[valid_positions[county_matches]] = True
            coordinates_outside_county[valid_positions] = ~county_matches

            # A county match proves that the point is in California. Only query
            # all county polygons for the small set of mismatches, which still
            # distinguishes an incorrect county from a point outside the state.
            fallback_positions = np.flatnonzero(~county_matches)
            if fallback_positions.size:
                boundary_tree = shapely.STRtree(np.asarray(all_geometries))
                fallback_pairs = boundary_tree.query(
                    points[fallback_positions], predicate="intersects"
                )
                if fallback_pairs.shape[1]:
                    fallback_inside = np.unique(fallback_pairs[0])
                    coordinates_in_california[
                        valid_positions[fallback_positions[fallback_inside]]
                    ] = True

    result["coordinates_in_california"] = coordinates_in_california
    result["coordinates_outside_county_flag"] = coordinates_outside_county
    return result


# Flag values that aren't possible
def flag_nono_values(df, columns):
    for column in columns:
        df[f"{column}Flag"] = df[column] < 0
    return df


def clean_frames(listing, sold, *, zip_path=ZIP_CODE_PATH, county_path=COUNTY_BOUNDARY_PATH, retain_unmapped_zip=False):
    listing = listing.copy()
    sold = sold.copy()

    listing = clean_duplicate_columns(listing)

    listing_date_columns = ["ListingContractDate", "ContractStatusChangeDate"]
    sold_date_columns = [
        "ListingContractDate",
        "PurchaseContractDate",
        "CloseDate",
        "ContractStatusChangeDate",
    ]

    listing = to_datetime(listing, listing_date_columns)
    sold = to_datetime(sold, sold_date_columns)

    sold["listing_after_close_flag"] = (
        sold["ListingContractDate"] > sold["CloseDate"]
    )
    sold["purchase_after_close_flag"] = (
        sold["PurchaseContractDate"] > sold["CloseDate"]
    )
    sold["negative_timeline_flag"] = (
        sold["ListingContractDate"] > sold["PurchaseContractDate"]
    )

    # Clear invalid listing dates.
    listing_after_close = sold[sold["listing_after_close_flag"]]
    sold.loc[listing_after_close.index, "ListingContractDate"] = pd.NaT

    listing = list_agent_drop(listing)
    sold = list_agent_drop(sold)

    listing["ListAgentFullName"] = (
        listing["ListAgentFullName"].str.strip().str.title()
    )
    sold["ListAgentFullName"] = sold["ListAgentFullName"].str.strip().str.title()

    listing["ListOfficeName"] = listing["ListOfficeName"].str.strip().str.title()
    sold["ListOfficeName"] = sold["ListOfficeName"].str.strip().str.title()

    # Filter to California properties and California ZIP codes.
    listing = listing[listing["StateOrProvince"] == "CA"]
    sold = sold[sold["StateOrProvince"] == "CA"]

    valid_zip_codes = set(
        pd.read_csv(
            zip_path,
            dtype={"ZIP_CODE": "string"},
        )["ZIP_CODE"]
    )
    listing = filter_zip_codes(listing, valid_zip_codes, retain_unmapped=retain_unmapped_zip)
    sold = filter_zip_codes(sold, valid_zip_codes, retain_unmapped=retain_unmapped_zip)

    listing["City"] = listing["City"].fillna("Unknown")
    sold["City"] = sold["City"].fillna("Unknown")

    listing["PropertySubType"] = listing["PropertySubType"].fillna("Unknown")
    sold["PropertySubType"] = sold["PropertySubType"].fillna("Unknown")

    county_boundaries = load_county_boundaries(county_path)
    listing = flag_coordinates(listing, county_boundaries)
    sold = flag_coordinates(sold, county_boundaries)

    listing_columns = [
        "DaysOnMarket",
        "BedroomsTotal",
        "BathroomsTotalInteger",
    ]
    sold_columns = listing_columns + ["ClosePrice"]

    listing = flag_nono_values(listing, listing_columns)
    sold = flag_nono_values(sold, sold_columns)

    # Flag properties with LivingArea less than 80 square feet.
    listing["LivingAreaFlag"] = listing["LivingArea"] < 80
    sold["LivingAreaFlag"] = sold["LivingArea"] < 80

    print(
        sold[
            [
                "DaysOnMarketFlag",
                "BedroomsTotalFlag",
                "BathroomsTotalIntegerFlag",
                "LivingAreaFlag",
            ]
        ].value_counts()
    )

    # Clear missing PropertySubType values.
    listing["PropertySubType"] = listing["PropertySubType"].fillna("Unknown")
    sold["PropertySubType"] = sold["PropertySubType"].fillna("Unknown")

    """
    Dropping redundant columns
    - PropertyType: Assumed to be `Residential`
    - MlsStatus and StandardStatus: Constant `Closed` values
    Authoritative ListingKey is retained for production revision resolution.
    """
    sold.drop(
        columns=[
            "PropertyType",
            "MlsStatus",
            "StandardStatus",
            "BuyerAgencyCompensationType",
            "OriginatingSystemSubName",
            "AttachedGarageYN",
            "FireplaceYN",
        ],
        inplace=True,
        errors="ignore",
    )

    # Fix known data-entry errors.
    to_drop = ["P1-22708", "41049105", "41079356"]
    sold = sold[~sold["ListingId"].isin(to_drop)]

    close_price_fixes = {
        "219137367DA": 1750000,
        "224002893": 1150000,
        "219113154PS": 380000,
        "V1-31998": 500000,
        "219134383PS": 485000,
        "P1-17580": 675000,
    }
    for listing_id, value in close_price_fixes.items():
        sold.loc[sold["ListingId"] == listing_id, "ClosePrice"] = value

    original_list_price_fixes = {
        "PI24198548": 525000,
        "OC24065101": 695000,
    }
    for listing_id, value in original_list_price_fixes.items():
        match = sold["ListingId"] == listing_id
        sold.loc[match, "OriginalListPrice"] = value
        sold.loc[match, "ListPrice"] = value

    return listing, sold


def main():
    listing, sold = clean_frames(pd.read_csv(LISTING_PATH, low_memory=False), pd.read_csv(SOLD_PATH, low_memory=False))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    listing.to_csv(OUTPUT_DIR / "CRMLSListing_cleaned.csv", index=False)
    sold.to_csv(OUTPUT_DIR / "CRMLSSold_cleaned.csv", index=False)


if __name__ == "__main__":
    main()
