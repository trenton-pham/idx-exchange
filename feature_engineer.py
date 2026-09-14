"""Reusable sale feature engineering with valid denominators."""
from pathlib import Path
import numpy as np
import pandas as pd

def engineer_features(sold):
    sold=sold.copy()
    for column in ("CloseDate","ListingContractDate","PurchaseContractDate"):
        sold[column]=pd.to_datetime(sold[column],errors="coerce",utc=True)
    price=pd.to_numeric(sold["ClosePrice"],errors="coerce")
    original=pd.to_numeric(sold["OriginalListPrice"],errors="coerce")
    area=pd.to_numeric(sold["LivingArea"],errors="coerce")
    sold["PriceRatio"]=(price/original.where(original>0)).replace([np.inf,-np.inf],np.nan)
    sold["CloseToOriginalListRatio"]=sold["PriceRatio"]
    sold["PricePerSqFt"]=(price/area.where(area>=80)).replace([np.inf,-np.inf],np.nan)
    sold["Year"]=sold["CloseDate"].dt.year
    sold["Month"]=sold["CloseDate"].dt.month
    sold["YrMo"]=sold["CloseDate"].dt.strftime("%Y-%m")
    sold["ListingToContractDays"]=(sold["PurchaseContractDate"]-sold["ListingContractDate"]).dt.days
    sold["ContractToCloseDays"]=(sold["CloseDate"]-sold["PurchaseContractDate"]).dt.days
    return sold

def main():
    target=Path("data/feature_engineer/CRMLSSold_feature_engineered.csv")
    target.parent.mkdir(parents=True,exist_ok=True)
    engineer_features(pd.read_csv("data/cleaned/CRMLSSold_cleaned.csv",low_memory=False)).to_csv(target,index=False)

if __name__=="__main__": main()
