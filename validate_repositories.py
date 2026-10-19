
from pathlib import Path

import pandas as pd

file_path = Path("data/raw/repositories_stage2.csv")

if not file_path.exists():
    raise SystemExit("Khong tim thay file CSV!")

df = pd.read_csv(file_path)

print("=== KIEM TRA CHAT LUONG DU LIEU ===")
print("So dong:", len(df))
print("So cot:", len(df.columns))
print("So repo_id duy nhat:", df["repo_id"].nunique())
print("So repo_id bi thieu:", df["repo_id"].isna().sum())
print("So dong trung lap:", df.duplicated(subset=["repo_id"]).sum())

print("\n=== GIA TRI THIEU ===")
print(df.isna().sum().sort_values(ascending=False))

print("\n=== NGAY TAO REPOSITORY ===")
df["created_at"] = pd.to_datetime(
    df["created_at"], errors="coerce", utc=True
)

print("Ngay tao som nhat:", df["created_at"].min())
print("Ngay tao moi nhat:", df["created_at"].max())

print("\n=== 5 DONG DAU TIEN ===")
print(df.head().to_string(index=False))


print("\n=== TONG KET KIEM TRA ===")
print("Tong so dong:", len(df))
print("Repo ID duy nhat:", df["repo_id"].nunique())
print("Repo ID bi thieu:", df["repo_id"].isna().sum())
print(
    "So dong trung lap:",
    df.duplicated(subset=["repo_id"]).sum()
)