
from pathlib import Path

import pandas as pd

# ==================================================
# 1. CAU HINH
# ==================================================

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

DEV_FILE = PROCESSED / "developers_stage2_master.csv"

START_DATE = pd.Timestamp("2020-01-01", tz="UTC")
END_DATE = pd.Timestamp("2026-10-20 23:59:59", tz="UTC")

ACTIVITY_CONFIG = {
    "Commits": {
        "file": RAW / "commits_stage2.csv",
        "date": "author_date",
        "author": "author_login",
        "repo": "repository",
        "keys": ["repository", "sha"],
    },
    "Issues": {
        "file": RAW / "issues_stage2.csv",
        "date": "created_at",
        "author": "author_login",
        "repo": "repository",
        "keys": ["id"],
    },
    "Pull Requests": {
        "file": RAW / "pull_requests_stage2.csv",
        "date": "created_at",
        "author": "author_login",
        "repo": "repository",
        "keys": ["id"],
    },
}

PROCESSED.mkdir(parents=True, exist_ok=True)


# ==================================================
# 2. DOC DEVELOPER MASTER
# ==================================================

if not DEV_FILE.exists():
    raise SystemExit(
        "Khong tim thay developers_stage2_master.csv"
    )

dev = pd.read_csv(
    DEV_FILE,
    encoding="utf-8-sig",
    dtype="string",
)

required_dev_columns = {
    "login",
    "country_or_region",
    "type",
}

missing_columns = required_dev_columns - set(dev.columns)

if missing_columns:
    raise SystemExit(
        f"Developer Master thieu cot: {missing_columns}"
    )

dev["login_key"] = (
    dev["login"].fillna("").str.strip().str.lower()
)

dev = dev[dev["login_key"] != ""].copy()

# Moi login chi giu mot ho so
dev = dev.drop_duplicates(
    subset=["login_key"],
    keep="last",
)

profile_map = (
    dev.set_index("login_key")[
        ["country_or_region", "type"]
    ].to_dict("index")
)


def classify_author(login):
    """Gan nhom quoc gia dua tren profile da thu thap."""

    if pd.isna(login) or not str(login).strip():
        return "No Author Login", "No Author Login"

    key = str(login).strip().lower()
    profile = profile_map.get(key)

    if profile is None:
        return "Unprofiled", "Unprofiled"

    country = profile.get("country_or_region")
    account_type = profile.get("type")

    country = (
        str(country).strip()
        if pd.notna(country)
        else "Unknown"
    )

    account_type = (
        str(account_type).strip().lower()
        if pd.notna(account_type)
        else "unknown"
    )

    if account_type != "user":
        return "Non-user account", "Non-user account"

    if country.lower() == "vietnam":
        return "Vietnam", "Vietnam"

    if country.lower() in {
        "",
        "unknown",
        "other/unknown",
        "nan",
        "none",
    }:
        return "Unresolved location", "Unresolved location"

    # Cac location duoc nhan dien thanh quoc gia/vung
    return "International", country


# ==================================================
# 3. XU LY TUNG BANG HOAT DONG
# ==================================================

summary_rows = []
country_rows = []
monthly_rows = []
quality_rows = []

for activity_name, config in ACTIVITY_CONFIG.items():
    path = config["file"]

    print(f"\n=== {activity_name} ===")

    if not path.exists():
        print("Bo qua file khong ton tai:", path)
        continue

    df = pd.read_csv(
        path,
        encoding="utf-8-sig",
        low_memory=False,
        dtype={
            config["author"]: "string",
            config["repo"]: "string",
        },
    )

    keys = config["keys"]
    required_columns = set(
        keys + [
            config["date"],
            config["author"],
            config["repo"],
        ]
    )

    missing = required_columns - set(df.columns)

    if missing:
        print("Thieu cot:", missing)
        continue

    # Bao cao khoa trung truoc khi loai trung
    duplicate_count = int(
        df.duplicated(subset=keys).sum()
    )

    missing_key_count = int(
        df[keys].isna().any(axis=1).sum()
    )

    raw_rows = len(df)

    # Loai trung trong bo nho, khong sua file raw
    df = df.drop_duplicates(
        subset=keys,
        keep="first",
    ).copy()

    dates = pd.to_datetime(
        df[config["date"]],
        errors="coerce",
        utc=True,
    )

    valid_date = dates.notna()

    in_range = (
        valid_date
        & (dates >= START_DATE)
        & (dates <= END_DATE)
    )

    before_range = int(
        (valid_date & (dates < START_DATE)).sum()
    )

    after_range = int(
        (valid_date & (dates > END_DATE)).sum()
    )

    invalid_date = int((~valid_date).sum())

    # Chi phan tich ban ghi nam trong khoang nghien cuu
    analysis = df.loc[in_range].copy()

    analysis["_event_date"] = dates.loc[in_range]
    analysis["_month"] = (
        analysis["_event_date"].dt.strftime("%Y-%m")
    )

    analysis["_login"] = (
        analysis[config["author"]]
        .fillna("")
        .str.strip()
        .str.lower()
    )

    analysis["_repo"] = analysis[config["repo"]]

    classifications = analysis["_login"].apply(
        classify_author
    )

    analysis["_country_group"] = classifications.apply(
        lambda item: item[0]
    )

    analysis["_country_detail"] = classifications.apply(
        lambda item: item[1]
    )

    analysis["_record"] = 1

    # ------------------------------------------
    # 3A. CHAT LUONG VA PHAM VI NGAY
    # ------------------------------------------

    quality_rows.append({
        "activity_type": activity_name,
        "raw_rows": raw_rows,
        "unique_rows_after_dedup": len(df),
        "duplicate_rows_in_raw": duplicate_count,
        "rows_missing_key": missing_key_count,
        "rows_in_research_period": len(analysis),
        "rows_with_invalid_date": invalid_date,
        "rows_before_period": before_range,
        "rows_after_period": after_range,
        "oldest_date_in_source": (
            str(dates[valid_date].min())
            if valid_date.any()
            else None
        ),
        "newest_date_in_source": (
            str(dates[valid_date].max())
            if valid_date.any()
            else None
        ),
    })

    # ------------------------------------------
    # 3B. VIETNAM VS INTERNATIONAL
    # ------------------------------------------

    grouped = analysis.groupby(
        "_country_group",
        dropna=False,
    ).agg(
        records=("_record", "sum"),
        unique_authors=("_login", lambda s: s[s != ""].nunique()),
        repositories=("_repo", "nunique"),
    ).reset_index()

    for _, row in grouped.iterrows():
        summary_rows.append({
            "activity_type": activity_name,
            "group": row["_country_group"],
            "records": int(row["records"]),
            "unique_authors": int(row["unique_authors"]),
            "repositories": int(row["repositories"]),
        })

    # Tinh ty le Vietnam trong cac ban ghi da nhan dien quoc gia
    identified = analysis[
        analysis["_country_group"].isin(
            ["Vietnam", "International"]
        )
    ]

    identified_total = len(identified)
    vietnam_total = int(
        (identified["_country_group"] == "Vietnam").sum()
    )
    international_total = int(
        (identified["_country_group"] == "International").sum()
    )

    vietnam_share = (
        vietnam_total / identified_total * 100
        if identified_total
        else 0
    )

    print("So dong trong khoang:", len(analysis))
    print("Dong trung khoa trong file raw:", duplicate_count)
    print("Ban ghi Vietnam:", vietnam_total)
    print("Ban ghi quoc te da nhan dien:", international_total)
    print("Ban ghi chua xac dinh/khong phai User:", len(analysis) - identified_total)
    print(
        "Ty le Vietnam trong nhom da nhan dien: "
        f"{vietnam_share:.2f}%"
    )

    # ------------------------------------------
    # 3C. PHAN BO QUOC GIA/VUNG CHI TIET
    # ------------------------------------------

    country_grouped = analysis.groupby(
        ["_country_group", "_country_detail"],
        dropna=False,
    ).agg(
        records=("_record", "sum"),
        unique_authors=("_login", lambda s: s[s != ""].nunique()),
        repositories=("_repo", "nunique"),
    ).reset_index()

    for _, row in country_grouped.iterrows():
        country_rows.append({
            "activity_type": activity_name,
            "country_group": row["_country_group"],
            "country_or_region": row["_country_detail"],
            "records": int(row["records"]),
            "unique_authors": int(row["unique_authors"]),
            "repositories": int(row["repositories"]),
        })

    # ------------------------------------------
    # 3D. XU HUONG THEO THANG
    # Chi dung de phan tich mo ta
    # ------------------------------------------

    monthly = analysis[
        analysis["_country_group"].isin(
            ["Vietnam", "International"]
        )
    ].groupby(
        ["_month", "_country_group"]
    ).agg(
        records=("_record", "sum"),
        unique_authors=("_login", lambda s: s[s != ""].nunique()),
    ).reset_index()

    for _, row in monthly.iterrows():
        monthly_rows.append({
            "activity_type": activity_name,
            "month": row["_month"],
            "group": row["_country_group"],
            "records": int(row["records"]),
            "unique_authors": int(row["unique_authors"]),
        })


# ==================================================
# 4. LUU CAC BANG PHAN TICH
# ==================================================

def save_table(rows, filename):
    if not rows:
        print("Khong co du lieu de luu:", filename)
        return

    output = PROCESSED / filename

    pd.DataFrame(rows).to_csv(
        output,
        index=False,
        encoding="utf-8-sig",
    )

    print("Da luu:", output)


save_table(
    summary_rows,
    "vietnam_vs_international_summary.csv",
)

save_table(
    country_rows,
    "country_activity_detailed.csv",
)

save_table(
    monthly_rows,
    "monthly_vietnam_international.csv",
)

save_table(
    quality_rows,
    "comparison_data_quality.csv",
)


# ==================================================
# 5. TONG KET CUOI
# ==================================================

print("\n=== HOAN TAT SO SANH ===")

if summary_rows:
    summary_df = pd.DataFrame(summary_rows)

    print(
        summary_df[
            [
                "activity_type",
                "group",
                "records",
                "unique_authors",
                "repositories",
            ]
        ].to_string(index=False)
    )

print(
    "\nLuu y: location la thong tin tu khai bao. "
    "Ket qua la so lieu mo ta cua dataset da thu thap, "
    "khong dai dien cho toan bo GitHub."
)
print("Khong goi GitHub API; khong sua file raw.")
