
from pathlib import Path

import pandas as pd

# ==================================================
# 1. CAU HINH
# ==================================================

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

START_DATE = pd.Timestamp("2020-01-01 00:00:00", tz="UTC")
END_DATE = pd.Timestamp("2026-10-20 23:59:59", tz="UTC")

PROCESSED.mkdir(parents=True, exist_ok=True)

TABLES = {
    "Repositories": {
        "path": RAW / "repositories_stage2.csv",
        "keys": ["repo_id"],
        "date_column": "created_at",
        "repo_column": None,
    },
    "Commits": {
        "path": RAW / "commits_stage2.csv",
        "keys": ["repository", "sha"],
        "date_column": "author_date",
        "repo_column": "repository",
    },
    "Issues": {
        "path": RAW / "issues_stage2.csv",
        "keys": ["id"],
        "date_column": "created_at",
        "repo_column": "repository",
    },
    "Pull Requests": {
        "path": RAW / "pull_requests_stage2.csv",
        "keys": ["id"],
        "date_column": "created_at",
        "repo_column": "repository",
    },
    "Developers": {
        "path": PROCESSED / "developers_stage2_master.csv",
        "keys": ["login"],
        "date_column": None,
        "repo_column": None,
    },
}

audit_rows = []
loaded_data = {}

# ==================================================
# 2. DOC VA KIEM TRA TUNG BANG
# ==================================================

print("=" * 65)
print("FINAL AUDIT - GITHUB DEVELOPER ANALYTICS")
print("Khoang thoi gian: 2020-01-01 den 2026-10-20")
print("=" * 65)

for table_name, config in TABLES.items():
    path = config["path"]

    print(f"\n--- {table_name} ---")

    if not path.exists():
        print("KHONG TIM THAY FILE:", path)
        audit_rows.append({
            "table": table_name,
            "file": str(path),
            "rows": None,
            "unique_keys": None,
            "missing_key_rows": None,
            "duplicate_key_rows": None,
            "repositories_covered": None,
            "date_valid_rows": None,
            "date_missing_or_invalid": None,
            "date_before_range": None,
            "date_in_range": None,
            "date_after_range": None,
            "status": "FILE_MISSING",
        })
        continue

    try:
        df = pd.read_csv(
            path,
            encoding="utf-8-sig",
            low_memory=False,
        )
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        print("KHONG DOC DUOC FILE:", error)
        audit_rows.append({
            "table": table_name,
            "file": str(path),
            "rows": None,
            "unique_keys": None,
            "missing_key_rows": None,
            "duplicate_key_rows": None,
            "repositories_covered": None,
            "date_valid_rows": None,
            "date_missing_or_invalid": None,
            "date_before_range": None,
            "date_in_range": None,
            "date_after_range": None,
            "status": "READ_ERROR",
        })
        continue

    loaded_data[table_name] = df

    print("File:", path)
    print("So dong:", len(df))
    print("So cot:", len(df.columns))

    # ---- Kiem tra khoa dinh danh ----
    keys = config["keys"]
    existing_keys = [key for key in keys if key in df.columns]

    if len(existing_keys) == len(keys):
        missing_keys = int(
            df[keys].isna().any(axis=1).sum()
        )

        duplicate_rows = int(
            df.duplicated(subset=keys).sum()
        )

        unique_keys = int(
            df.dropna(subset=keys)
            .drop_duplicates(subset=keys)
            .shape[0]
        )

        print("So khoa duy nhat:", unique_keys)
        print("So dong thieu khoa:", missing_keys)
        print("So dong trung khoa:", duplicate_rows)
    else:
        missing_keys = None
        duplicate_rows = None
        unique_keys = None

        print("CANH BAO: Thieu cot khoa:", set(keys) - set(df.columns))

    # ---- Kiem tra do phu repository ----
    repo_column = config["repo_column"]
    repo_coverage = None

    if repo_column and repo_column in df.columns:
        repo_coverage = int(df[repo_column].nunique(dropna=True))
        print("So repository co trong bang:", repo_coverage)

    # ---- Kiem tra khoang thoi gian ----
    date_column = config["date_column"]

    date_valid = None
    date_missing_invalid = None
    before_range = None
    in_range = None
    after_range = None

    if date_column:
        if date_column not in df.columns:
            print("CANH BAO: Khong co cot ngay:", date_column)
        else:
            dates = pd.to_datetime(
                df[date_column],
                utc=True,
                errors="coerce",
            )

            valid_dates = dates.notna()

            date_valid = int(valid_dates.sum())
            date_missing_invalid = int((~valid_dates).sum())
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

            print("Ngay hop le:", date_valid)
            print("Ngay thieu/khong doc duoc:", date_missing_invalid)
            print("Ban ghi truoc khoang:", before_range)
            print("Ban ghi trong khoang:", in_range)
            print("Ban ghi sau khoang:", after_range)

            if date_valid:
                print("Ngay som nhat:", dates.min())
                print("Ngay moi nhat:", dates.max())

    # ---- Trang thai so bo ----
    status = "CHECK"

    if (
        existing_keys == keys
        and missing_keys == 0
        and duplicate_rows == 0
    ):
        status = "KEYS_OK"

    audit_rows.append({
        "table": table_name,
        "file": str(path),
        "rows": len(df),
        "unique_keys": unique_keys,
        "missing_key_rows": missing_keys,
        "duplicate_key_rows": duplicate_rows,
        "repositories_covered": repo_coverage,
        "date_valid_rows": date_valid,
        "date_missing_or_invalid": date_missing_invalid,
        "date_before_range": before_range,
        "date_in_range": in_range,
        "date_after_range": after_range,
        "status": status,
    })


# ==================================================
# 3. KIEM TRA DO PHU QUOC GIA DEVELOPER
# ==================================================

country_rows = []

if "Developers" in loaded_data:
    dev_df = loaded_data["Developers"]

    print("\n" + "=" * 65)
    print("DEVELOPER COUNTRY COVERAGE")
    print("=" * 65)

    if "country_or_region" in dev_df.columns:
        country_counts = (
            dev_df["country_or_region"]
            .fillna("Unknown")
            .astype(str)
            .str.strip()
            .replace("", "Unknown")
            .value_counts()
        )

        for country, count in country_counts.items():
            country_rows.append({
                "country_or_region": country,
                "developer_profiles": int(count),
            })

        print(country_counts.to_string())

        total_profiles = len(dev_df)
        vietnam_count = int(
            (dev_df["country_or_region"] == "Vietnam").sum()
        )

        known_count = int(
             (~dev_df["country_or_region"].isin(
                ["Unknown", "Other/Unknown"]
                 )).sum()
)

        print("\nTong profile:", total_profiles)
        print("Profile gan Vietnam:", vietnam_count)
        print(
            "Profile co nhom quoc gia/vung nhan dien:",
            known_count,
        )
        print(
            "Ty le gan Vietnam: {:.2f}%".format(
                vietnam_count / total_profiles * 100
                if total_profiles else 0
            )
        )
    else:
        print("Khong co cot country_or_region.")


# ==================================================
# 4. TONG HOP VA LUU BAO CAO
# ==================================================

audit_df = pd.DataFrame(audit_rows)

audit_file = PROCESSED / "final_audit_report.csv"
audit_df.to_csv(
    audit_file,
    index=False,
    encoding="utf-8-sig",
)

country_file = PROCESSED / "developer_country_distribution.csv"

if country_rows:
    pd.DataFrame(country_rows).to_csv(
        country_file,
        index=False,
        encoding="utf-8-sig",
    )

# Tong so dong cua cac bang nghiep vu, khong phai
# so doi tuong duy nhat sau khi gop lien bang
business_tables = [
    "Repositories",
    "Commits",
    "Issues",
    "Pull Requests",
]

total_rows = sum(
    len(loaded_data[name])
    for name in business_tables
    if name in loaded_data
)

print("\n" + "=" * 65)
print("TONG KET CUOI")
print("=" * 65)

print("Tong dong cua 4 bang nghiep vu:", total_rows)
print("Luu y: day la tong dong giua cac bang, khong phai")
print("so doi tuong duy nhat khi gop lien bang.")

print("\nBao cao audit:", audit_file)

if country_rows:
    print("Bao cao quoc gia:", country_file)

print("\nHoan tat kiem ke. Khong thay doi file raw.")
