
from pathlib import Path

import pandas as pd

# ==========================================
# 1. CAU HINH
# ==========================================

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

REPO_FILE = RAW / "repositories_stage2.csv"

START_DATE = pd.Timestamp("2020-01-01", tz="UTC")
END_DATE = pd.Timestamp("2026-10-20 23:59:59", tz="UTC")

TABLES = {
    "Commits": {
        "file": RAW / "commits_stage2.csv",
        "repo_col": "repository",
        "date_col": "author_date",
        "keys": ["repository", "sha"],
    },
    "Issues": {
        "file": RAW / "issues_stage2.csv",
        "repo_col": "repository",
        "date_col": "created_at",
        "keys": ["id"],
    },
    "Pull Requests": {
        "file": RAW / "pull_requests_stage2.csv",
        "repo_col": "repository",
        "date_col": "created_at",
        "keys": ["id"],
    },
}

PROCESSED.mkdir(parents=True, exist_ok=True)


def normalize_repo(values):
    return (
        values.astype("string")
        .str.strip()
        .str.casefold()
    )


# ==========================================
# 2. DOC DANH SACH REPOSITORY GOC
# ==========================================

if not REPO_FILE.exists():
    raise SystemExit("Khong tim thay repositories_stage2.csv")

repos_df = pd.read_csv(
    REPO_FILE,
    encoding="utf-8-sig",
    dtype={"repo_id": "string", "full_name": "string"},
)

if not {"repo_id", "full_name"}.issubset(repos_df.columns):
    raise SystemExit("File repository thieu repo_id hoac full_name")

repos_df = repos_df.dropna(subset=["full_name"]).copy()
repos_df["repo_key"] = normalize_repo(repos_df["full_name"])

repos_df = repos_df.drop_duplicates(
    subset=["repo_key"],
    keep="first",
)

repo_keys = set(repos_df["repo_key"].dropna())

activity_df = repos_df[["repo_id", "full_name", "repo_key"]].copy()

print("=" * 65)
print("REPOSITORY COVERAGE AUDIT")
print("=" * 65)
print("So repository goc:", len(activity_df))


# ==========================================
# 3. KIEM TRA TUNG BANG HOAT DONG
# ==========================================

summary_rows = []

for table_name, config in TABLES.items():
    path = config["file"]
    repo_col = config["repo_col"]
    date_col = config["date_col"]
    keys = config["keys"]

    print(f"\n--- {table_name} ---")

    if not path.exists():
        print("Khong tim thay file:", path.name)

        activity_df[f"{table_name}_count"] = 0

        summary_rows.append({
            "table": table_name,
            "total_rows": 0,
            "unique_repositories_in_file": 0,
            "repositories_covered_from_seed": 0,
            "repositories_with_zero_records": len(activity_df),
            "records_with_unknown_repository": 0,
            "missing_key_rows": None,
            "duplicate_key_rows": None,
            "date_invalid_or_missing": None,
            "date_before_range": None,
            "date_in_range": None,
            "date_after_range": None,
            "oldest_date": None,
            "newest_date": None,
            "status": "FILE_MISSING",
        })
        continue

    df = pd.read_csv(
        path,
        encoding="utf-8-sig",
        low_memory=False,
        dtype={repo_col: "string"},
    )

    required_columns = set(keys + [repo_col])

    if not required_columns.issubset(df.columns):
        missing_columns = required_columns - set(df.columns)

        print("Thieu cot:", missing_columns)

        activity_df[f"{table_name}_count"] = 0

        summary_rows.append({
            "table": table_name,
            "total_rows": len(df),
            "unique_repositories_in_file": None,
            "repositories_covered_from_seed": None,
            "repositories_with_zero_records": None,
            "records_with_unknown_repository": None,
            "missing_key_rows": None,
            "duplicate_key_rows": None,
            "date_invalid_or_missing": None,
            "date_before_range": None,
            "date_in_range": None,
            "date_after_range": None,
            "oldest_date": None,
            "newest_date": None,
            "status": "MISSING_COLUMNS",
        })
        continue

    df["_repo_key"] = normalize_repo(df[repo_col])

    known_repo_mask = df["_repo_key"].isin(repo_keys)

    covered_repos = set(
        df.loc[known_repo_mask, "_repo_key"].dropna()
    )

    # Dem so dong cho tung repository trong danh sach goc
    counts = (
        df.loc[known_repo_mask]
        .groupby("_repo_key")
        .size()
    )

    count_column = f"{table_name}_count"

    activity_df[count_column] = (
        activity_df["repo_key"]
        .map(counts)
        .fillna(0)
        .astype("int64")
    )

    # Kiem tra khoa dinh danh
    missing_key_rows = int(
        df[keys].isna().any(axis=1).sum()
    )

    duplicate_key_rows = int(
        df.duplicated(subset=keys).sum()
    )

    # Kiem tra ngay
    if date_col in df.columns:
        dates = pd.to_datetime(
            df[date_col],
            errors="coerce",
            utc=True,
        )

        valid_dates = dates.notna()

        date_invalid_or_missing = int((~valid_dates).sum())

        before_range = int(
            (valid_dates & (dates < START_DATE)).sum()
        )

        in_range = int(
            (
                valid_dates
                & (dates >= START_DATE)
                & (dates <= END_DATE)
            ).sum()
        )

        after_range = int(
            (valid_dates & (dates > END_DATE)).sum()
        )

        oldest_date = (
            str(dates.min()) if valid_dates.any() else None
        )

        newest_date = (
            str(dates.max()) if valid_dates.any() else None
        )
    else:
        date_invalid_or_missing = None
        before_range = None
        in_range = None
        after_range = None
        oldest_date = None
        newest_date = None

    zero_count = int((activity_df[count_column] == 0).sum())
    unknown_repo_records = int((~known_repo_mask).sum())

    print("Tong so dong:", len(df))
    print("Repository co ban ghi khop danh sach goc:", len(covered_repos))
    print("Repository khong co ban ghi:", zero_count)
    print("Dong khong khop danh sach repository goc:", unknown_repo_records)
    print("Khoa bi thieu:", missing_key_rows)
    print("Dong trung khoa:", duplicate_key_rows)

    if in_range is not None:
        print("Ban ghi trong khoang ngay:", in_range)
        print("Ban ghi truoc khoang:", before_range)
        print("Ban ghi sau khoang:", after_range)
        print("Ngay som nhat:", oldest_date)
        print("Ngay moi nhat:", newest_date)

    summary_rows.append({
        "table": table_name,
        "total_rows": len(df),
        "unique_repositories_in_file": int(
            df["_repo_key"].nunique(dropna=True)
        ),
        "repositories_covered_from_seed": len(covered_repos),
        "repositories_with_zero_records": zero_count,
        "records_with_unknown_repository": unknown_repo_records,
        "missing_key_rows": missing_key_rows,
        "duplicate_key_rows": duplicate_key_rows,
        "date_invalid_or_missing": date_invalid_or_missing,
        "date_before_range": before_range,
        "date_in_range": in_range,
        "date_after_range": after_range,
        "oldest_date": oldest_date,
        "newest_date": newest_date,
        "status": "AUDITED",
    })


# ==========================================
# 4. LUU BAO CAO VA DANH SACH REPOSITORY
# ==========================================

activity_df = activity_df.drop(columns=["repo_key"])

summary_df = pd.DataFrame(summary_rows)

coverage_file = PROCESSED / "repository_coverage_audit.csv"
activity_file = PROCESSED / "repository_activity_counts.csv"

summary_df.to_csv(
    coverage_file,
    index=False,
    encoding="utf-8-sig",
)

activity_df = activity_df.sort_values(
    by=[
        "Pull Requests_count",
        "Issues_count",
        "Commits_count",
    ],
    ascending=False,
)

activity_df.to_csv(
    activity_file,
    index=False,
    encoding="utf-8-sig",
)

print("\n" + "=" * 65)
print("HOAN TAT KIEM TRA DO PHU")
print("=" * 65)

print("Bao cao tong hop:", coverage_file)
print("Bao cao tung repository:", activity_file)

print("\n10 repository co nhieu hoat dong nhat:")
print(
    activity_df[
        [
            "full_name",
            "Commits_count",
            "Issues_count",
            "Pull Requests_count",
        ]
    ].head(10).to_string(index=False)
)

print("\nKhong sua file raw va khong goi GitHub API.")
