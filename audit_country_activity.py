
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

DEV_FILE = PROCESSED / "developers_stage2_master.csv"

ACTIVITY_FILES = {
    "Commits": RAW / "commits_stage2.csv",
    "Issues": RAW / "issues_stage2.csv",
    "Pull Requests": RAW / "pull_requests_stage2.csv",
}

if not DEV_FILE.exists():
    raise SystemExit("Khong tim thay developers_stage2_master.csv")

developers = pd.read_csv(
    DEV_FILE,
    encoding="utf-8-sig",
    dtype="string",
)

required = {"login", "country_or_region"}

if not required.issubset(developers.columns):
    raise SystemExit("Bang Developer thieu login hoac country_or_region")

developers = developers.dropna(subset=["login"]).copy()
developers["login_key"] = developers["login"].str.strip().str.lower()

# Moi login chi giu mot ho so
developers = developers.drop_duplicates(
    subset=["login_key"],
    keep="last",
)

country_map = developers.set_index("login_key")["country_or_region"].to_dict()

summary_rows = []
distribution_rows = []
unmatched_rows = []

for table_name, file_path in ACTIVITY_FILES.items():
    print(f"\n=== {table_name} ===")

    if not file_path.exists():
        print("Khong tim thay file:", file_path.name)
        continue

    df = pd.read_csv(
        file_path,
        encoding="utf-8-sig",
        dtype="string",
        low_memory=False,
    )

    if "author_login" not in df.columns:
        print("Khong co cot author_login:", file_path.name)
        continue

    df["author_key"] = df["author_login"].str.strip().str.lower()
    df["country_or_region"] = df["author_key"].map(country_map)

    # Phan biet khong co login, khong co profile va profile chua ro quoc gia
    no_login = df["author_key"].isna() | df["author_key"].eq("")
    unprofiled = ~no_login & df["country_or_region"].isna()

    df.loc[no_login, "country_or_region"] = "No Author Login"
    df.loc[unprofiled, "country_or_region"] = "Unprofiled"

    df["country_or_region"] = (
        df["country_or_region"]
        .fillna("Unknown")
        .replace("", "Unknown")
    )

    known_country = ~df["country_or_region"].isin(
        ["Unknown", "Other/Unknown", "Unprofiled", "No Author Login"]
    )

    vietnam_mask = df["country_or_region"].eq("Vietnam")

    print("So ban ghi:", len(df))
    print("So author login duy nhat:", df["author_key"].nunique())
    print("Ban ghi gan duoc nhom quoc gia:", int(known_country.sum()))
    print("Ban ghi gan Vietnam:", int(vietnam_mask.sum()))
    print("Ban ghi chua xac dinh duoc quoc gia:",
          int((~known_country).sum()))

    summary_rows.append({
        "table": table_name,
        "total_rows": len(df),
        "unique_author_logins": df["author_key"].nunique(),
        "rows_with_recognized_country": int(known_country.sum()),
        "rows_vietnam": int(vietnam_mask.sum()),
        "rows_unknown_or_unprofiled": int((~known_country).sum()),
        "country_coverage_pct": round(
            known_country.mean() * 100, 2
        ) if len(df) else 0,
    })

    country_counts = (
        df["country_or_region"]
        .value_counts()
        .rename_axis("country_or_region")
        .reset_index(name="record_count")
    )

    country_counts.insert(0, "table", table_name)
    distribution_rows.extend(country_counts.to_dict("records"))

    # Ghi lai login chua co profile de xem xet sau
    if unprofiled.any():
        missing = (
            df.loc[unprofiled, "author_login"]
            .value_counts()
            .rename_axis("login")
            .reset_index(name="record_count")
        )
        missing.insert(0, "table", table_name)
        unmatched_rows.extend(missing.to_dict("records"))

PROCESSED.mkdir(parents=True, exist_ok=True)

summary_file = PROCESSED / "country_activity_coverage.csv"
distribution_file = PROCESSED / "country_activity_distribution.csv"
unmatched_file = PROCESSED / "unprofiled_activity_authors.csv"

pd.DataFrame(summary_rows).to_csv(
    summary_file, index=False, encoding="utf-8-sig"
)

pd.DataFrame(distribution_rows).to_csv(
    distribution_file, index=False, encoding="utf-8-sig"
)

pd.DataFrame(unmatched_rows).to_csv(
    unmatched_file, index=False, encoding="utf-8-sig"
)

print("\n=== HOAN TAT ===")
print("Bao cao do phu:", summary_file)
print("Phan bo theo quoc gia:", distribution_file)
print("Author chua co profile:", unmatched_file)
print("Khong goi GitHub API; khong sua file raw.")
