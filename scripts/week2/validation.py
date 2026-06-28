import pandas as pd
import os

RAW_DIR = "../../data/raw/"
PROCESSED_DIR = "../../data/processed/"

def process_data():
    """
    Copied from process.py in week 1 script
    """
    START_YEAR = 2024
    CURR_YEAR = 2026
    CURR_MONTH = 5
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

            listing_file = f"{RAW_DIR}CRMLSListing{year}{month:02d}.csv"

            if os.path.exists(listing_file):
                df_listing = pd.read_csv(listing_file, low_memory=False)

            else:
                continue

            filled_sold_file = f"{RAW_DIR}CRMLSSold{year}{month:02d}_filled.csv"
            
            if os.path.exists(filled_sold_file):
                df_sold = pd.read_csv(filled_sold_file, low_memory=False)
            
            else:
                base_sold_file = f"{RAW_DIR}CRMLSSold{year}{month:02d}.csv"
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

    listing_comb.to_csv(os.path.join(PROCESSED_DIR, "CRMLSListing_202401_202605_all.csv"), index=False)
    sold_comb.to_csv(os.path.join(PROCESSED_DIR, "CRMLSSold_202401_202605_all.csv"), index=False)

def unique_property_types(data):
    return data["PropertyType"].unique()
    

def missing_value_analysis(data):
    missing_values = data.isna().sum().sort_values(ascending=False)
    missing_df = pd.DataFrame(missing_values, columns=["missing_count"])
    missing_df["missing_pct"] = (missing_df["missing_count"] / data.shape[0]) * 100
    return missing_df

def main():
    # Process all dates into one csv first
    process_data()

    # Listing data
    listing_data = pd.read_csv(PROCESSED_DIR + "CRMLSListing_202401_202605_all.csv", low_memory=False)
    missing_listing = missing_value_analysis(listing_data)

    missing_listing_filtered = missing_listing[missing_listing["missing_pct"] > 90]
    print(missing_listing_filtered.index.tolist())

    """
    Columns with > 90% missing values in the listing data (descending order):
        ['FireplacesTotal', 'MiddleOrJuniorSchoolDistrict', 'AboveGradeFinishedArea', 'BusinessType', 
        'TaxYear', 'CoveredSpaces', 'TaxAnnualAmount', 'ElementarySchoolDistrict', 'BelowGradeFinishedArea', 
        'CoBuyerAgentFirstName', 'BuilderName', 'LotSizeDimensions', 'BuildingAreaTotal']
    """

    property_listing = unique_property_types(listing_data)
    print(property_listing)

    """
    Unique property types for listing:
    [ 'ManufacturedInPark',      'CommercialSale',         'Residential',
    'ResidentialLease',                'Land',   'ResidentialIncome',
     'CommercialLease', 'BusinessOpportunity']
    """

    # Sold data
    sold_data = pd.read_csv(PROCESSED_DIR + "CRMLSSold_202401_202605_all.csv")
    missing_sold = missing_value_analysis(sold_data)

    missing_sold_filtered = missing_sold[missing_sold["missing_pct"] > 90]
    print(missing_sold_filtered.index.to_list())

    """
    Columns with > 90% missing values in the sold data (descending order):
        ['AboveGradeFinishedArea', 'CoveredSpaces', 'TaxAnnualAmount', 'TaxYear', 'ElementarySchoolDistrict', 
        'FireplacesTotal', 'MiddleOrJuniorSchoolDistrict', 'BusinessType', 'WaterfrontYN', 'BelowGradeFinishedArea', 
        'BasementYN', 'LotSizeDimensions', 'BuilderName', 'BuildingAreaTotal', 'CoBuyerAgentFirstName']
    """

    property_sold = unique_property_types(sold_data)
    print(property_sold)

    """
    Unique property types for listing:
    [        'Residential',     'CommercialLease',                'Land',
    'ResidentialLease',  'ManufacturedInPark',   'ResidentialIncome',
      'CommercialSale', 'BusinessOpportunity']
    """

if __name__ == "__main__":
    main()