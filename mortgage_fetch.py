"""FRED MORTGAGE30US, averaged without listing weights."""
from io import StringIO
from pathlib import Path
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SOURCE_URL="https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"

def monthly_rates(weekly):
    weekly=weekly.copy(); weekly.columns=["date","rate_30yr_fixed"]
    weekly["date"]=pd.to_datetime(weekly["date"],errors="coerce")
    weekly["rate_30yr_fixed"]=pd.to_numeric(weekly["rate_30yr_fixed"],errors="coerce")
    weekly["year_month"]=weekly["date"].dt.to_period("M").astype(str)
    return weekly.dropna(subset=["date"]).groupby("year_month",as_index=False)["rate_30yr_fixed"].mean()

def fetch_rates():
    session=requests.Session()
    session.mount("https://",HTTPAdapter(max_retries=Retry(total=4,backoff_factor=1,status_forcelist=[429,500,502,503,504])))
    response=session.get(SOURCE_URL,timeout=45); response.raise_for_status()
    return monthly_rates(pd.read_csv(StringIO(response.text)))

def enrich(frame,rates,date_column):
    result=frame.copy()
    result["year_month"]=pd.to_datetime(result[date_column],errors="coerce",utc=True).dt.strftime("%Y-%m")
    result=result.drop(columns=["rate_30yr_fixed"],errors="ignore")
    return result.merge(rates,on="year_month",how="left",validate="many_to_one")

def main():
    rates=fetch_rates(); target=Path("data/mortgage"); target.mkdir(parents=True,exist_ok=True)
    for kind,column in (("Listing","ListingContractDate"),("Sold","CloseDate")):
        frame=pd.read_csv(f"data/filtered/CRMLS{kind}_filtered.csv",low_memory=False)
        enrich(frame,rates,column).to_csv(target/f"CRMLS{kind}_with_mortgage.csv",index=False)

if __name__=="__main__": main()
