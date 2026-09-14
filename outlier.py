"""Historical three-IQR and 0.75–1.50 price-ratio policy."""
from pathlib import Path
import pandas as pd

def filter_outliers(frame):
    q1,q3=frame["ClosePrice"].quantile([0.25,0.75]); iqr=q3-q1
    return frame.loc[frame["ClosePrice"].between(q1-3*iqr,q3+3*iqr)&frame["CloseToOriginalListRatio"].between(0.75,1.5)].copy()

def main():
    target=Path("data/post_outlier/CRMLSSold_cleaned_out.csv")
    target.parent.mkdir(parents=True,exist_ok=True)
    filter_outliers(pd.read_csv("data/feature_engineer/CRMLSSold_feature_engineered.csv",low_memory=False)).to_csv(target,index=False)

if __name__=="__main__": main()
