
import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# =========================================
# 1. CAU HINH
# =========================================

load_dotenv()
token = os.getenv("GITHUB_TOKEN")

if not token:
    raise SystemExit("Khong tim thay GITHUB_TOKEN trong .env")

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"

CANDIDATE_FILE = RAW / "vietnam_developer_candidates.csv"
OUTPUT_FILE = RAW / "vietnam_developer_profiles.csv"

if not CANDIDATE_FILE.exists():
    raise SystemExit("Khong tim thay vietnam_developer_candidates.csv")

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

session = requests.Session()
session.headers.update(headers)

# =========================================
# 2. DOC UNG VIEN
# =========================================

candidates_df = pd.read_csv(
    CANDIDATE_FILE,
    encoding="utf-8-sig",
    dtype="string",
)

candidates_df = (
    candidates_df.dropna(subset=["login"])
    .drop_duplicates(subset=["login"])
)

print("So tai khoan ung vien:", len(candidates_df))

# Doc cac profile da lay truoc do de co the chay tiep
if OUTPUT_FILE.exists():
    old_df = pd.read_csv(
        OUTPUT_FILE,
        encoding="utf-8-sig",
        dtype={"login": "string"},
    )
    done_logins = set(old_df["login"].dropna().str.lower())
else:
    old_df = pd.DataFrame()
    done_logins = set()

print("Profile ung vien da lay:", len(done_logins))

# =========================================
# 3. LAY PROFILE TU GITHUB API
# =========================================

new_profiles = []
not_found = []
stop_collection = False

for index, row in enumerate(
    candidates_df.to_dict(orient="records"),
    start=1,
):
    login = str(row["login"]).strip()

    if not login or login.lower() in done_logins:
        continue

    url = f"https://api.github.com/users/{login}"

    print(f"\n[{index}/{len(candidates_df)}] Dang lay: {login}")

    user = None

    for attempt in range(4):
        try:
            response = session.get(url, timeout=30)
        except requests.RequestException as error:
            print("Loi ket noi:", error)

            if attempt == 3:
                stop_collection = True
                break

            time.sleep(15 * (attempt + 1))
            continue

        if response.status_code == 200:
            user = response.json()
            break

        if response.status_code == 404:
            print("Khong tim thay tai khoan:", login)
            not_found.append({
                "login": login,
                "reason": "404_not_found",
            })
            break

        message = response.text[:300].lower()

        rate_limited = (
            response.status_code == 429
            or "rate limit" in message
            or bool(response.headers.get("Retry-After"))
            or response.headers.get("X-RateLimit-Remaining") == "0"
        )

        if response.status_code in (403, 429) and rate_limited:
            retry_after = response.headers.get("Retry-After")

            if retry_after and retry_after.isdigit():
                wait_seconds = int(retry_after)
            else:
                wait_seconds = 60 * (attempt + 1)

            print(
                f"GitHub gioi han request. "
                f"Cho {wait_seconds} giay..."
            )

            if attempt == 3:
                stop_collection = True
                break

            time.sleep(wait_seconds)
            continue

        print("API loi:", response.status_code)
        print(response.text[:300])
        stop_collection = True
        break

    if stop_collection:
        break

    if user is None:
        continue

    profile = {
        "user_id": user.get("id"),
        "login": user.get("login"),
        "name": user.get("name"),
        "company": user.get("company"),
        "location": user.get("location"),
        "bio": user.get("bio"),
        "type": user.get("type"),
        "public_repos": user.get("public_repos"),
        "public_gists": user.get("public_gists"),
        "followers": user.get("followers"),
        "following": user.get("following"),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
        "html_url": user.get("html_url"),
        "sources": "vietnam_location_search",
    }

    new_profiles.append(profile)
    done_logins.add(login.lower())

    # Luu sau moi profile de tranh mat tien do
    if new_profiles:
        current_df = pd.DataFrame(new_profiles)

        if not old_df.empty:
            combined = pd.concat(
                [old_df, current_df],
                ignore_index=True,
            )
        else:
            combined = current_df

        combined["_login_key"] = (
            combined["login"].astype("string").str.lower()
        )

        combined = combined.drop_duplicates(
            subset=["_login_key"],
            keep="first",
        ).drop(columns="_login_key")

        combined.to_csv(
            OUTPUT_FILE,
            index=False,
            encoding="utf-8-sig",
        )

        old_df = combined
        new_profiles = []

    print(
        f"Da luu: {login} | "
        f"Location: {user.get('location')}"
    )

    time.sleep(1.2)

# Luu danh sach tai khoan khong tim thay neu co
if not_found:
    pd.DataFrame(not_found).to_csv(
        RAW / "vietnam_developer_not_found.csv",
        index=False,
        encoding="utf-8-sig",
    )

print("\n=== TONG KET ===")
print("Tong profile da luu:", len(done_logins))
print("File:", OUTPUT_FILE)

if stop_collection:
    print("Da dung som; chay lai de tiep tuc tu profile chua lay.")
