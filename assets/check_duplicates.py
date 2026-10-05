import pandas as pd

df = pd.read_csv("datasets/college_details.csv")

print("Total rows:", len(df))
print("Unique college codes:", df["college_code"].nunique())

duplicates = df[df.duplicated(subset=["college_code"], keep=False)]

if duplicates.empty:
    print("✅ No duplicate college codes.")
else:
    print("❌ Duplicate college codes:")
    print(duplicates)

print("Missing college codes:", df["college_code"].isnull().sum())