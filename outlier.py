import pandas as pd

sold_path = "data/feature_engineer/CRMLSSold_feature_engineered.csv"
df = pd.read_csv(sold_path, low_memory=False)

Q1 = df['ClosePrice'].quantile(0.25) 
Q3 = df['ClosePrice'].quantile(0.75) 
IQR = Q3 - Q1 
lower = Q1 - 3.0 * IQR 
upper = Q3 + 3.0 * IQR 
df = df[(df['ClosePrice'] >= lower) & (df['ClosePrice'] <= upper)]

# Fix ClosePrice values that are incorrect
to_drop = ["P1-22708", "41049105", "41079356"]
df = df[~df["ListingId"].isin(to_drop)]

def fix_close_price(ListingId, value):
    df.loc[df["ListingId"] == ListingId, "ClosePrice"] = value

def fix_list_price(ListingId, value):
    df.loc[df["ListingId"] == ListingId, "ListPrice"] = value

fix_close_price("219137367DA", 1750000)
fix_close_price("224002893", 1150000)
fix_close_price("219113154PS", 380000)
fix_close_price("V1-31998", 500000)
fix_close_price("219134383PS", 485000)
fix_close_price("P1-17580", 675000)

fix_list_price("PI24198548", 525000)
fix_list_price("OC24065101", 695000)

df = df[df["CloseToOriginalListRatio"] <= 1.5]
df = df[df["CloseToOriginalListRatio"] >= 0.5]

df.to_csv("data/post_outlier/CRMLSSold_cleaned_out.csv", index=False)       