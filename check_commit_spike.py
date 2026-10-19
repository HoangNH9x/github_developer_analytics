
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW_FILE = ROOT / "data" / "raw" / "commits_stage2.csv"
MONTHLY_FILE = ROOT / "data" / "processed" / "monthly_activity.csv"

df = pd.read_csv(RAW_FILE, low_memory=False)

df["author_date"] = pd.to_datetime(
    df["author_date"], errors="coerce", utc=True
)
df["month"] = df["author_date"].dt.strftime("%Y-%m")

print("\n=== KIEM TRA COMMITS RAW ===")
print("Tong dong:", len(df))
print("SHA duy nhat:", df["sha"].nunique())
print("SHA bi trung:", df["sha"].duplicated().sum())
print("Ngay khong hop le:", df["author_date"].isna().sum())

monthly_raw = df.groupby("month").size().rename("raw_records")

print("\n=== 12 THANG GAN NHAT ===")
print(monthly_raw.tail(12).to_string())

october = df[df["month"] == "2026-10"]

print("\n=== KIEM TRA THANG 10/2026 ===")
print("So commits:", len(october))
print("Ty le tren toan bo commits:",
      f"{len(october) / len(df) * 100:.2f}%")

print("\nTop repository co nhieu commits trong thang 10:")
print(
    october.groupby("repository")
    .size()
    .sort_values(ascending=False)
    .head(10)
    .to_string()
)

# So sanh voi bang tong hop monthly_activity.csv
if MONTHLY_FILE.exists():
    monthly = pd.read_csv(MONTHLY_FILE, low_memory=False)
    monthly["table"] = monthly["table"].astype(str).str.strip()
    monthly = monthly[
        monthly["table"].str.casefold() == "commits"
    ].copy()

    monthly["month"] = pd.to_datetime(
        monthly["month"].astype(str),
        errors="coerce",
    ).dt.strftime("%Y-%m")

    monthly_calc = (
        monthly.groupby("month")["records"].sum()
    )

    comparison = pd.concat(
        [
            monthly_raw.rename("raw"),
            monthly_calc.rename("monthly_activity"),
        ],
        axis=1,
    ).fillna(0)

    comparison["difference"] = (
        comparison["raw"] - comparison["monthly_activity"]
    )

    print("\n=== DOI CHIEU RAW VA MONTHLY ACTIVITY ===")
    print("Tong raw co ngay hop le:", int(monthly_raw.sum()))
    print("Tong bang monthly_activity:", int(monthly_calc.sum()))
    print("Thang co chenh lech:")
    print(
        comparison[comparison["difference"] != 0]
        .to_string()
    )
