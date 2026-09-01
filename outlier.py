import pandas as pd

sold_path = "data/feature_engineer/CRMLSSold_feature_engineered.csv"
df = pd.read_csv(sold_path, low_memory=False)

Q1 = df['ClosePrice'].quantile(0.25) 
Q3 = df['ClosePrice'].quantile(0.75) 
IQR = Q3 - Q1 
lower = Q1 - 3.0 * IQR 
upper = Q3 + 3.0 * IQR 
df = df[(df['ClosePrice'] >= lower) & (df['ClosePrice'] <= upper)]

df = df[df["CloseToOriginalListRatio"] <= 1.5]
df = df[df["CloseToOriginalListRatio"] >= 0.75]

# confirm changed ClosePrice
print(df["ClosePrice"].loc[df["ListingId"] == "219137367DA"])
print(df["ClosePrice"].loc[df["ListingId"] == "224002893"])
print(df["ClosePrice"].loc[df["ListingId"] == "219113154PS"])
print(df["ClosePrice"].loc[df["ListingId"] == "V1-31998"])
print(df["ClosePrice"].loc[df["ListingId"] == "219134383PS"])
print(df["ClosePrice"].loc[df["ListingId"] == "P1-17580"])

print(df["OriginalListPrice"].loc[df["ListingId"] == "PI24198548"])
print(df["OriginalListPrice"].loc[df["ListingId"] == "OC24065101"])

df.to_csv("data/post_outlier/CRMLSSold_cleaned_out.csv", index=False)       