import pandas as pd

sold_path = "data/cleaned/CRMLSSold_cleaned.csv"
df = pd.read_csv(sold_path, low_memory=False)

print(f"Before outlier filtering", df.shape)
"""
Before row count: 443092
"""

Q1 = df['ClosePrice'].quantile(0.25) 
Q3 = df['ClosePrice'].quantile(0.75) 
IQR = Q3 - Q1 
lower = Q1 - 3.0 * IQR 
upper = Q3 + 3.0 * IQR 
df = df[(df['ClosePrice'] >= lower) & (df['ClosePrice'] <= upper)]

print(f"After outlier filtering", df.shape)
"""
After row count: 428928
"""

df.to_csv("data/post_outlier/CRMLSSold_cleaned_out.csv", index=False)