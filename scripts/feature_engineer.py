from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
sold_path = PROJECT_DIR / "data" / "cleaned" / "CRMLSSold_cleaned.csv"
date_columns = ["CloseDate", "ListingContractDate", "PurchaseContractDate"]

sold = pd.read_csv(sold_path, parse_dates=date_columns, low_memory=False)

sold["PriceRatio"] = sold["ClosePrice"] / sold["OriginalListPrice"]
sold["CloseToOriginalListRatio"] = sold["PriceRatio"]
sold["PricePerSqFt"] = sold["ClosePrice"] / sold["LivingArea"]

sold["Year"] = sold["CloseDate"].dt.year
sold["Month"] = sold["CloseDate"].dt.month
sold["YrMo"] = sold["CloseDate"].dt.strftime("%Y-%m")

sold["ListingToContractDays"] = (
    sold["PurchaseContractDate"] - sold["ListingContractDate"]
).dt.days
sold["ContractToCloseDays"] = (
    sold["CloseDate"] - sold["PurchaseContractDate"]
).dt.days

sold.to_csv(
    PROJECT_DIR / "data" / "feature_engineer" / "CRMLSSold_feature_engineered.csv",
    index=False,
)
