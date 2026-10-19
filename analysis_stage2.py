
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

START_DATE = pd.Timestamp("2020-01-01", tz="UTC")
END_DATE = pd.Timestamp("2026-10-20 23:59:59", tz="UTC")

PROCESSED.mkdir(parents=True, exist_ok=True)

CONFIG = {
    "Commits": {
        "file": RAW / "commits_stage2.csv",
        "date": "author_date",
        "repo": "repository",
        "key": ["repository", "sha"],
        "author": "author_login",
    },
    "Issues": {
        "file": RAW / "issues_stage2.csv",
        "date": "created_at",
        "repo": "repository",
        "key": ["id"],
        "author": "author_login",
    },
    "Pull Requests": {
        "file": RAW / "pull_requests_stage2.csv",
        "date": "created_at",
        "repo": "repository",
        "key": ["id"],
        "author": "author_login",
    },
}

monthly_results = []
quality_results = []
country_results = []
repo_results = []

# -----------------------------------------
# 1. DOC DEVELOPER MASTER
# -----------------------------------------

developer_file = PROCESSED / "developers_stage2_master.csv"

if developer_file.exists():
    developers = pd.read_csv(
        developer_file,
        encoding="utf-8-sig",
        dtype="string",
    )

    developers["login_key"] = (
        developers["login"].str.strip().str.lower()
    )

    country_map = (
        developers.dropna(subset=["login_key"])
        .drop_duplicates("login_key")
        .set_index("login_key")["country_or_region"]
        .to_dict()
    )
else:
    country_map = {}
    print("CANH BAO: Khong tim thay Developer Master.")

# -----------------------------------------
# 2. PHAN TICH TUNG BANG HOAT DONG
# -----------------------------------------

for table_name, config in CONFIG.items():
    path = config["file"]

    if not path.exists():
        print("Bo qua file khong ton tai:", path)
        continue

    df = pd.read_csv(
        path,
        encoding="utf-8-sig",
        low_memory=False,
        dtype={config["author"]: "string"},
    )

    date_col = config["date"]
    repo_col = config["repo"]
    key_cols = config["key"]
    author_col = config["author"]

    if date_col not in df.columns:
        print(f"Thieu cot ngay trong {table_name}")
        continue

    raw_rows = len(df)
    parsed_dates = pd.to_datetime(
        df[date_col], errors="coerce", utc=True
    )

    valid_date = parsed_dates.notna()
    in_range = (
        valid_date
        & (parsed_dates >= START_DATE)
        & (parsed_dates <= END_DATE)
    )

    # Bao cao pham vi ngay tren du lieu raw
    quality_results.append({
        "table": table_name,
        "raw_rows": raw_rows,
        "valid_dates": int(valid_date.sum()),
        "invalid_or_missing_dates": int((~valid_date).sum()),
        "rows_in_research_period": int(in_range.sum()),
        "rows_before_period": int(
            (valid_date & (parsed_dates < START_DATE)).sum()
        ),
        "rows_after_period": int(
            (valid_date & (parsed_dates > END_DATE)).sum()
        ),
        "oldest_valid_date": (
            str(parsed_dates[valid_date].min())
            if valid_date.any() else None
        ),
        "newest_valid_date": (
            str(parsed_dates[valid_date].max())
            if valid_date.any() else None
        ),
    })

    # Chi su dung ban ghi co ngay trong khoang nghien cuu
    analysis = df.loc[in_range].copy()
    analysis["event_date"] = parsed_dates.loc[in_range]
    analysis["month"] = analysis["event_date"].dt.strftime("%Y-%m")

    # Dem theo thang
    monthly = (
        analysis.groupby("month")
        .size()
        .rename("records")
        .reset_index()
    )
    monthly["table"] = table_name
    monthly_results.extend(monthly.to_dict("records"))

    # Dem hoat dong theo repository
    if repo_col in analysis.columns:
        repo_counts = (
            analysis.groupby(repo_col)
            .size()
            .rename("records")
            .reset_index()
            .rename(columns={repo_col: "repository"})
        )
        repo_counts["table"] = table_name
        repo_results.extend(repo_counts.to_dict("records"))

    # Gan quoc gia tu Developer Master
    if author_col in analysis.columns:
        login = analysis[author_col].astype("string").str.strip().str.lower()
        analysis["country_or_region"] = login.map(country_map)

        missing_login = login.isna() | login.eq("")
        analysis.loc[missing_login, "country_or_region"] = "No Author Login"

        analysis["country_or_region"] = (
            analysis["country_or_region"]
            .fillna("Unprofiled")
            .replace("", "Unknown")
        )

        counts = (
            analysis.groupby("country_or_region")
            .size()
            .rename("activity_records")
            .reset_index()
        )
        counts["table"] = table_name
        country_results.extend(counts.to_dict("records"))

    print(
        f"{table_name}: raw={raw_rows:,}, "
        f"in_period={len(analysis):,}"
    )

# -----------------------------------------
# 3. LUU CAC BANG KET QUA
# -----------------------------------------

def save_csv(rows, filename):
    if rows:
        pd.DataFrame(rows).to_csv(
            PROCESSED / filename,
            index=False,
            encoding="utf-8-sig",
        )
        print("Da luu:", PROCESSED / filename)


save_csv(quality_results, "analysis_data_quality.csv")
save_csv(monthly_results, "monthly_activity.csv")
save_csv(country_results, "activity_by_country.csv")
save_csv(repo_results, "activity_by_repository.csv")

# -----------------------------------------
# 4. TOM TAT
# -----------------------------------------

print("\n=== TONG KET PHAN TICH ===")

if quality_results:
    quality_df = pd.DataFrame(quality_results)
    print(
        quality_df[
            ["table", "raw_rows", "rows_in_research_period"]
        ].to_string(index=False)
    )

if country_results:
    country_df = pd.DataFrame(country_results)
    country_summary = (
        country_df.groupby("country_or_region")["activity_records"]
        .sum()
        .sort_values(ascending=False)
    )

    print("\n=== 15 NHOM QUOC GIA/VUNG CO NHIEU HOAT DONG ===")
    print(country_summary.head(15).to_string())

print("\nHoan tat. Khong goi GitHub API va khong sua file raw.")
