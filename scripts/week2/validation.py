import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import iqr
from statsmodels.stats.descriptivestats import Description
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

def distribution_summary(data):
    columns = ["ClosePrice", "LivingArea", "DaysOnMarket"]
    for column in columns:
        stat_desc = Description(data[column])
        print(f"Distribution Summary For {column}:\n")
        print(stat_desc.summary())
        print("\n")

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
    sold_data = pd.read_csv(PROCESSED_DIR + "CRMLSSold_202401_202605_all.csv", low_memory=False)
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

    distribution_summary(sold_data)

    """
    Distribution Summary For ClosePrice:
    Descriptive Statistics  
    ==========================
    nobs                639859
    missing                  7
    mean             8.802e+05
    std_err               6814
    upper_ci         8.936e+05
    lower_ci         8.669e+05
    std              5.451e+06
    iqr                1020000
    iqr_normal       7.561e+05
    mad              7.115e+05
    mad_normal       8.917e+05
    coef_var             6.193
    range            989500000
    max              989500000
    min                      0
    skew                 129.7
    kurtosis         1.866e+04
    jarque_bera      9.279e+12
    jarque_bera_pval         0
    mode                  3500
    mode_freq         0.006761
    median              630000
    1%                    1750
    5%                    2695
    10%                   3495
    25%                  55000
    50%                 630000
    75%                1075000
    90%                1792500
    95%                2500000
    99%                4999999
    --------------------------

    Distribution Summary For LivingArea:
    Descriptive Statistics     
    =================================
    nobs                       639859
    missing                     44831
    mean                         3369
    std_err                      1528
    upper_ci                     6364
    lower_ci                      374
    std                     1.179e+06
    iqr                           969
    iqr_normal                  718.3
    mad                          3279
    mad_normal                   4109
    coef_var                    349.9
    range                   909090909
    max                     909090909
    min                             0
    skew                          771
    kurtosis                5.946e+05
    jarque_bera      8765682720079100
    jarque_bera_pval                0
    mode                         1440
    mode_freq                0.006475
    median                       1580
    1%                            480
    5%                            733
    10%                           896
    25%                          1184
    50%                          1580
    75%                          2153
    90%                          2924
    95%                          3540
    99%                          5467
    ---------------------------------

    Distribution Summary For DaysOnMarket:
    Descriptive Statistics  
    ==========================
    nobs                639859
    missing                  0
    mean                  43.3
    std_err            0.08732
    upper_ci             43.47
    lower_ci             43.13
    std                  69.85
    iqr                     45
    iqr_normal           33.36
    mad                  38.45
    mad_normal           48.18
    coef_var             1.613
    range                12718
    max                  12430
    min                   -288
    skew                 16.85
    kurtosis              1749
    jarque_bera      8.131e+10
    jarque_bera_pval         0
    mode                     7
    mode_freq          0.03976
    median                  22
    1%                       0
    5%                       2
    10%                      4
    25%                      9
    50%                     22
    75%                     54
    90%                    104
    95%                    148
    99%                    292
    --------------------------
    """

if __name__ == "__main__":
    main()