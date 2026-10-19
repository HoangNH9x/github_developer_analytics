
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")

FILES = {
    "Repositories": {
        "file": "repositories_stage2.csv",
        "keys": ["repo_id"],
        "date_columns": ["created_at"],
    },
    "Commits": {
        "file": "commits_stage2.csv",
        "keys": ["repository", "sha"],
        "date_columns": ["author_date"],
    },
    "Issues": {
        "file": "issues_stage2.csv",
        "keys": ["id"],
        "date_columns": ["created_at"],
    },
    "Pull Requests": {
        "file": "pull_requests_stage2.csv",
        "keys": ["id"],
        "date_columns": ["created_at"],
    },
}

all_logins = set()

print("=== KIEM KE DU LIEU STAGE 2 ===")

for label, config in FILES.items():
    path = RAW / config["file"]

    if not path.exists():
        print(f"\n{label}: CHUA CO FILE")
        continue

    df = pd.read_csv(path, encoding="utf-8-sig")

    keys = config["keys"]
    existing_keys = [key for key in keys if key in df.columns]

    print(f"\n--- {label} ---")
    print("File:", path)
    print("So dong:", len(df))

    if len(existing_keys) == len(keys):
        print("So khoa duy nhat:", len(df.drop_duplicates(subset=keys)))
        print("So khoa bi thieu:", df[keys].isna().any(axis=1).sum())
        print("So dong trung khoa:", df.duplicated(subset=keys).sum())

    for column in config["date_columns"]:
        if column not in df.columns:
            continue

        dates = pd.to_datetime(df[column], utc=True, errors="coerce")
        print(f"{column} - ngay som nhat:", dates.min())
        print(f"{column} - ngay moi nhat:", dates.max())

    for column in ["owner_login", "author_login", "merged_by"]:
        if column in df.columns:
            values = df[column].dropna().astype(str).str.strip()
            all_logins.update(
                value for value in values
                if value and value.lower() not in {"nan", "none"}
            )

print("\n=== DEVELOPER CANDIDATES ===")
print("So login duy nhat tim thay trong cac file:", len(all_logins))
print("Day la so tai khoan ung vien, chua phai so ho so Developer da thu thap.")
