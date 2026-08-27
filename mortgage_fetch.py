import pandas as pd
import pathlib as Path
import os

# Fetch the mortgage rate data from FRED
url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"
mortgage = pd.read_csv(url, parse_dates=['observation_date'])
mortgage.columns = ['date', 'rate_30yr_fixed']

# Resample weekly rates to monthly averages
mortgage['year_month'] = mortgage['date'].dt.to_period('M')
mortgage_monthly = (
mortgage.groupby('year_month')['rate_30yr_fixed']
.mean()
.reset_index()
)
# Create a matching year_month key on the MLS datasets
# Sold dataset — key off CloseDate
sold_file_path = Path.Path("data/filtered/CRMLSSold_202401_202605_filtered.csv")
sold = pd.read_csv(sold_file_path, low_memory=False)
sold['year_month'] = pd.to_datetime(sold['CloseDate']).dt.to_period('M')
# Listings dataset — key off ListingContractDate

listings_file_path = Path.Path("data/filtered/CRMLSListing_202401_202605_filtered.csv")
listings = pd.read_csv(listings_file_path, low_memory=False)
listings['year_month'] = pd.to_datetime(
listings['ListingContractDate']
).dt.to_period('M')

# Merge
sold_with_rates = sold.merge(mortgage_monthly, on='year_month', how='left')
listings_with_rates = listings.merge(mortgage_monthly, on='year_month', how='left')
# Validate the merge
# Check for any unmatched rows (rate should not be null)
print(sold_with_rates['rate_30yr_fixed'].isnull().sum())
print(listings_with_rates['rate_30yr_fixed'].isnull().sum())
# Preview
print(
sold_with_rates[
['CloseDate', 'year_month', 'ClosePrice', 'rate_30yr_fixed']
].head()
)

# Save new datasets with mortgage rates
output_dir = Path.Path("data/mortgage")
listings_with_rates.to_csv(os.path.join(output_dir, "CRMLSListing_202401_202605_with_mortgage.csv"), index=False)
sold_with_rates.to_csv(os.path.join(output_dir, "CRMLSSold_202401_202605_with_mortgage.csv"), index=False)
