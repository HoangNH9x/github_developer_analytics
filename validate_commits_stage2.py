
from pathlib import Path

import pandas as pd

file_path = Path("data/raw/commits_stage2.csv")

if not file_path.exists():
    raise SystemExit("Khong tim thay file commits_stage2.csv")

df = pd.read_csv(file_path, encoding="utf-8-sig")

required_columns = ["repository", "sha"]

for column in required_columns:
    if column not in df.columns:
        raise SystemExit(f"Thieu cot bat buoc: {column}")

print("=== KIEM TRA DU LIEU COMMITS ===")
print("Tong so dong:", len(df))
print("So repository:", df["repository"].nunique())
print("So SHA duy nhat:", df["sha"].nunique())
print("Repository bi thieu:", df["repository"].isna().sum())
print("SHA bi thieu:", df["sha"].isna().sum())

# Kiem tra trung lap theo repository va SHA
print(
    "Commit trung lap:",
    df.duplicated(subset=["repository", "sha"]).sum()
)

# Kiem tra BOM co the xuat hien khi noi file CSV
bom_counts = {}

for column in df.select_dtypes(include="object").columns:
    bom_counts[column] = (
        df[column]
        .fillna("")
        .astype(str)
        .str.contains("\ufeff", regex=False)
        .sum()
    )

print("\n=== KIEM TRA KY TU BOM ===")
for column, count in bom_counts.items():
    if count > 0:
        print(f"{column}: {count} gia tri co BOM")

print("\n=== SO DONG THEO REPOSITORY ===")
print(df.groupby("repository").size().sort_values(
    ascending=False
).head(10))

print("\n=== 5 DONG DAU TIEN ===")
print(df.head().to_string(index=False))
