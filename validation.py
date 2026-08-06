import pandas as pd
from statsmodels.stats.descriptivestats import Description
from pathlib import Path
import os

RAW_DIR = Path("data/raw/")
PROCESSED_DIR = Path("data/processed/")
FILTERED_DIR = Path("data/filtered/")

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

    listing_comb.to_csv(os.path.join(PROCESSED_DIR, "CRMLSListing_202401_202605.csv"), index=False)
    sold_comb.to_csv(os.path.join(PROCESSED_DIR, "CRMLSSold_202401_202605.csv"), index=False)

def unique_property_types(data):
    return data["PropertyType"].unique()
    

def missing_value_analysis(data):
    missing_values = data.isna().sum().sort_values(ascending=False)
    missing_df = pd.DataFrame(missing_values, columns=["missing_count"])
    missing_df["missing_pct"] = (missing_df["missing_count"] / data.shape[0]) * 100
    return missing_df

def filter_missing_columns(data, threshold=50):
    missing_df = missing_value_analysis(data)
    columns_to_drop = missing_df[missing_df["missing_pct"] > threshold].index.tolist()
    filtered_data = data.drop(columns=columns_to_drop)
    return filtered_data, columns_to_drop

def distribution_summary(data):
    columns = ["ClosePrice", "LivingArea", "DaysOnMarket"]
    for column in columns:
        stat_desc = Description(data[column])
        print(f"Distribution Summary For {column}:\n")
        print(stat_desc.summary())
        print("\n")

def main():
    # Process all dates into one csv first
    # process_data()

    # Listing data
    listing_data = pd.read_csv(os.path.join(PROCESSED_DIR, Path("CRMLSListing_202401_202605.csv")), low_memory=False)
    missing_listing = missing_value_analysis(listing_data)

    missing_listing_filtered = missing_listing[missing_listing["missing_pct"] > 90]
    print(missing_listing_filtered.index.tolist())

    """
    Columns with > 90% missing values in the listing data (descending order):
        - 'FireplacesTotal'
        - 'MiddleOrJuniorSchoolDistrict'
        - 'AboveGradeFinishedArea'
        - 'BusinessType', 
        - 'TaxYear'
        - 'CoveredSpaces'
        - 'TaxAnnualAmount'
        - 'ElementarySchoolDistrict'
        - 'BelowGradeFinishedArea', 
        - 'CoBuyerAgentFirstName', 
        - 'BuilderName'
        - 'LotSizeDimensions'
        - 'BuildingAreaTotal'
    """

    # property_listing = unique_property_types(listing_data)
    # print(property_listing)

    """
    Unique property types for listing:
    [ 'ManufacturedInPark',      'CommercialSale',         'Residential',
    'ResidentialLease',                'Land',   'ResidentialIncome',
     'CommercialLease', 'BusinessOpportunity']
    """

    # Sold data
    sold_data = pd.read_csv(os.path.join(PROCESSED_DIR, Path("CRMLSSold_202401_202605.csv")), low_memory=False)
    missing_sold = missing_value_analysis(sold_data)

    missing_sold_filtered = missing_sold[missing_sold["missing_pct"] > 90]
    print(missing_sold_filtered.index.to_list())

    """
    Columns with > 90% missing values in the sold data (descending order):
        - 'AboveGradeFinishedArea'
        - 'CoveredSpaces'
        - 'TaxAnnualAmount'
        - 'TaxYear'
        - 'ElementarySchoolDistrict', 
        - 'FireplacesTotal'
        - 'MiddleOrJuniorSchoolDistrict'
        - 'BusinessType'
        - 'WaterfrontYN'
        - 'BelowGradeFinishedArea', 
        - 'BasementYN'
        - 'LotSizeDimensions'
        - 'BuilderName'
        - 'BuildingAreaTotal'
        - 'CoBuyerAgentFirstName'
    """

    # property_sold = unique_property_types(sold_data)
    # print(property_sold)

    """
    Unique property types for listing:
    [        'Residential',     'CommercialLease',                'Land',
    'ResidentialLease',  'ManufacturedInPark',   'ResidentialIncome',
      'CommercialSale', 'BusinessOpportunity']
    """

    distribution_summary(sold_data)

    """
      Descriptive Statistics  
==========================
nobs                447964
missing                  2
mean             1.193e+06
std_err               9052
upper_ci          1.21e+06
lower_ci         1.175e+06
std              6.059e+06
iqr                 725000
iqr_normal       5.374e+05
mad              7.204e+05
mad_normal       9.029e+05
coef_var              5.08
range            989500000
max              989500000
min                      0
skew                 119.3
kurtosis         1.559e+04
jarque_bera      4.535e+12
jarque_bera_pval         0
mode                750000
mode_freq         0.007447
median              825000
1%               2.005e+05
5%                  340000
10%                 415000
25%                 575000
50%                 825000
75%                1300000
90%                2075000
95%              2.858e+06
99%                5600000
--------------------------


Distribution Summary For LivingArea:

  Descriptive Statistics  
==========================
nobs                447964
missing                253
mean                  1904
std_err              38.04
upper_ci              1979
lower_ci              1830
std              2.546e+04
iqr                    976
iqr_normal           723.5
mad                  719.5
mad_normal           901.7
coef_var             13.37
range             17021321
max               17021321
min                      0
skew                 667.5
kurtosis         4.463e+05
jarque_bera      3.716e+15
jarque_bera_pval         0
mode                  1200
mode_freq         0.003556
median                1646
1%                     605
5%                     840
10%                    985
25%                   1248
50%                   1646
75%                   2224
90%                   2984
95%                   3564
99%                   5288
--------------------------


Distribution Summary For DaysOnMarket:

  Descriptive Statistics  
==========================
nobs                447964
missing                  0
mean                 37.31
std_err            0.08011
upper_ci             37.47
lower_ci             37.16
std                  53.62
iqr                     40
iqr_normal           29.65
mad                  33.05
mad_normal           41.42
coef_var             1.437
range                12718
max                  12430
min                   -288
skew                 30.85
kurtosis              6404
jarque_bera      7.648e+11
jarque_bera_pval         0
mode                     7
mode_freq          0.04707
median                  18
1%                       0
5%                       1
10%                      4
25%                      8
50%                     18
75%                     48
90%                     94
95%                    132
99%                    233
--------------------------
    """

    ### Filter columns with > 90% missing values
    listing_data_filtered, listing_dropped_columns = filter_missing_columns(listing_data, threshold=90)
    sold_data_filtered, sold_dropped_columns = filter_missing_columns(sold_data, threshold=90)

    listing_data_filtered.to_csv(os.path.join(FILTERED_DIR, "CRMLSListing_202401_202605_filtered.csv"), index=False)
    sold_data_filtered.to_csv(os.path.join(FILTERED_DIR, "CRMLSSold_202401_202605_filtered.csv"), index=False)

if __name__ == "__main__":
    main()