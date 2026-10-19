
import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("GITHUB_TOKEN")

if not token:
    raise SystemExit("Khong tim thay GITHUB_TOKEN trong .env")

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"

SOURCES = {
    "repositories_stage2.csv": ["owner_login"],
    "commits_stage2.csv": ["author_login"],
    "issues_stage2.csv": ["author_login"],
    "pull_requests_stage2.csv": ["author_login", "merged_by"],
}

PROFILE_FILE = RAW / "developers_stage2.csv"
OUTPUT_FILE = RAW / "vietnam_developer_candidates.csv"

# Cac cach khai bao location co the lien quan Viet Nam
QUERIES = [
    "location:Vietnam type:user",
    'location:"Viet Nam" type:user',
    "location:Hanoi type:user",
    'location:"Ho Chi Minh City" type:user',
    "location:Saigon type:user",
    'location:"Da Nang" type:user',
]

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

session = requests.Session()
session.headers.update(headers)


def load_logins():
    logins = set()

    for filename, columns in SOURCES.items():
        path = RAW / filename

        if not path.exists():
            print("Bo qua file chua co:", filename)
            continue

        try:
            df = pd.read_csv(
                path,
                encoding="utf-8-sig",
                dtype="string",
                usecols=lambda col: col in columns,
            )
        except (ValueError, pd.errors.EmptyDataError):
            continue

        for column in columns:
            if column not in df.columns:
                continue

            values = df[column].dropna().str.strip()

            logins.update(
                value.lower()
                for value in values
                if value and value.lower() not in {"nan", "none"}
            )

    return logins


activity_logins = load_logins()

# Ho so da lay thi khong can lay lai
existing_logins = set()

if PROFILE_FILE.exists():
    profiles = pd.read_csv(
        PROFILE_FILE,
        encoding="utf-8-sig",
        dtype="string",
        usecols=["login"],
    )

    existing_logins = set(
        profiles["login"].dropna().str.lower()
    )

print("Tai khoan co trong du lieu hoat dong:", len(activity_logins))
print("Developer profiles da co:", len(existing_logins))

hits = {}

for query in QUERIES:
    print("\nDang tim:", query)

    for page in range(1, 4):
        try:
            response = session.get(
                "https://api.github.com/search/users",
                params={
                    "q": query,
                    "per_page": 100,
                    "page": page,
                },
                timeout=30,
            )
        except requests.RequestException as error:
            print("Loi ket noi:", error)
            break

        if response.status_code != 200:
            print("HTTP Status:", response.status_code)
            print(response.text[:300])
            print("Tam dung truy van nay.")
            break

        result = response.json()
        items = result.get("items", [])

        if not items:
            break

        for item in items:
            login = item.get("login")

            if not login:
                continue

            key = login.lower()

            # Chi giu tai khoan co hoat dong trong dataset cua minh
            if key not in activity_logins:
                continue

            # Bo qua ho so da thu thap
            if key in existing_logins:
                continue

            if key not in hits:
                hits[key] = {
                    "login": login,
                    "search_queries": set(),
                    "html_url": item.get("html_url"),
                    "user_type": item.get("type"),
                }

            hits[key]["search_queries"].add(query)

        print(
            f"Trang {page}: {len(items)} ket qua tim kiem | "
            f"Khop dataset: {len(hits)}"
        )

        # Giu toc do thap de han che rate limit
        time.sleep(2)

        if len(items) < 100:
            break

rows = []

for item in hits.values():
    rows.append({
        "login": item["login"],
        "search_queries": " | ".join(
            sorted(item["search_queries"])
        ),
        "user_type": item["user_type"],
        "html_url": item["html_url"],
    })

df = pd.DataFrame(
    rows,
    columns=[
        "login",
        "search_queries",
        "user_type",
        "html_url",
    ],
)

if not df.empty:
    df = df.drop_duplicates(subset=["login"])

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

print("\n=== KET QUA ===")
print("Tai khoan hoat dong khop tim kiem:", len(df))
print("File:", OUTPUT_FILE)
print("Chua goi API lay them ho so profile.")
