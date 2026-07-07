import pandas as pd
import matplotlib.pyplot as plt

"""
Analyzing numeric distribution of the following fields: 
- ClosePrice
- ListPrice
- OriginalListPrice
- LivingArea
- LotSizeAcres
- BedroomsTotal
- BathroomsTotalInteger
- DaysOnMarket
- YearBuilt
"""

def summary_stats(df):
    columns = ["ClosePrice", "ListPrice", "OriginalListPrice", "LivingArea", 
               "LotSizeAcres", "BedroomsTotal", "BathroomsTotalInteger", 
               "DaysOnMarket", "YearBuilt"]
    
    for column in columns:

        """
        Note: Outliers are excluded in visualizations for readability, but the
        raw data will be present in the summary statistic.
        """

        data = df.get(column)
        q1 = data.quantile(q=0.25)
        q3 = data.quantile(q=0.75)
        data_iqr = q3 - q1
        lower_bound = q1 - (1.5 * data_iqr)
        upper_bound = q3 + (1.5 * data_iqr)
        data_filtered = data[(data > lower_bound) & (data < upper_bound)]

        hist(data_filtered, column)
        box(data_filtered, column)

        data_desc = pd.DataFrame(data.describe())
        data_desc.to_csv(f"summary_stat/{column}_stat.csv")

def hist(series, column):
    plt.figure()
    plt.hist(series, bins=30)
    plt.title(f"Distribution of {column}")
    plt.ylabel("Count")
    plt.savefig(f"visuals/{column.lower()}_hist.pdf", format="pdf")

def box(series, column):
    plt.figure()
    plt.boxplot(series, orientation="h")
    plt.title(f"Distribution of {column}")
    plt.savefig(f"visuals/{column.lower()}_box.pdf", format="pdf")

def main():
    PROCESSED_DIR = "../../data/processed/"

    # listing_data = pd.read_csv(PROCESSED_DIR + "CRMLSListing_202401_202605.csv", low_memory=False)
    sold_data = pd.read_csv(PROCESSED_DIR + "CRMLSSold_202401_202605.csv", low_memory=False)

    summary_stats(sold_data)

if __name__ == "__main__":
    main()