
import os
import time
from collections import Counter
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

ACTIVITY_FILES = [
    RAW / "commits_stage2.csv",
    RAW / "issues_stage2.csv",
    RAW / "pull_requests_stage2.csv",
]

BASE_PROFILE = ROOT / "data" / "processed" / "developers_stage2_master.csv"
VIETNAM_PROFILE = RAW / "vietnam_developer_profiles.csv"

OUTPUT_FILE = RAW / "developers_activity_profiles.csv"
CHECKPOINT_FILE = RAW / "developers_activity_profiles_checkpoint.csv"

MAX_NEW_PROFILES = 2000
REQUEST_DELAY = 1.2

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

session = requests.Session()
session.headers.update(headers)


# =========================================
# 2. TAO DANH SACH AUTHOR VA DEM HOAT DONG
# =========================================

activity_counts = Counter()
display_names = {}

for file_path in ACTIVITY_FILES:
    if not file_path.exists():
        print("Bo qua file chua co:", file_path.name)
        continue

    try:
        df = pd.read_csv(
            file_path,
            encoding="utf-8-sig",
            usecols=lambda col: col == "author_login",
            dtype="string",
            low_memory=False,
        )
    except (ValueError, pd.errors.EmptyDataError):
        print("Khong co cot author_login:", file_path.name)
        continue

    if "author_login" not in df.columns:
        continue

    logins = df["author_login"].dropna().str.strip()
    logins = logins[
        logins.ne("")
        & ~logins.str.lower().isin(["nan", "none", "null"])
    ]

    counts = logins.str.lower().value_counts()

    activity_counts.update(counts.to_dict())

    for login in logins:
        display_names.setdefault(login.lower(), login)

print("So author login trong du lieu:", len(activity_counts))


# =========================================
# 3. DOC CAC PROFILE DA CO
# =========================================

known_logins = set()


def add_existing_logins(file_path):
    if not file_path.exists():
        return

    try:
        df = pd.read_csv(
            file_path,
            encoding="utf-8-sig",
            usecols=["login"],
            dtype="string",
        )
    except (ValueError, pd.errors.EmptyDataError):
        return

    known_logins.update(
        df["login"].dropna().str.strip().str.lower()
    )


add_existing_logins(BASE_PROFILE)
add_existing_logins(VIETNAM_PROFILE)
add_existing_logins(OUTPUT_FILE)

# Tai khoan da xu ly, ke ca 404, khong thu lai lien tuc
finished_logins = set()

if CHECKPOINT_FILE.exists():
    checkpoint = pd.read_csv(
        CHECKPOINT_FILE,
        encoding="utf-8-sig",
        dtype="string",
    )

    if {"login", "status"}.issubset(checkpoint.columns):
        finished_logins.update(
            checkpoint.loc[
                checkpoint["status"].isin(["ok", "not_found"]),
                "login",
            ].dropna().str.lower()
        )

print("Profile da co:", len(known_logins))
print("Author da xu ly qua checkpoint:", len(finished_logins))


# =========================================
# 4. CHON TOI DA 2000 AUTHOR CON THIEU PROFILE
# =========================================

candidates = []

for login_key, count in activity_counts.most_common():
    if login_key in known_logins or login_key in finished_logins:
        continue

    candidates.append({
        "login": display_names[login_key],
        "login_key": login_key,
        "activity_count": count,
    })

candidates = candidates[:MAX_NEW_PROFILES]

print("So profile moi du kien:", len(candidates))


# =========================================
# 5. LUU CHECKPOINT
# =========================================

def record_checkpoint(login, status, activity_count):
    row = pd.DataFrame([{
        "login": login,
        "status": status,
        "activity_count": activity_count,
    }])

    exists = (
        CHECKPOINT_FILE.exists()
        and CHECKPOINT_FILE.stat().st_size > 0
    )

    row.to_csv(
        CHECKPOINT_FILE,
        mode="a",
        header=not exists,
        index=False,
        encoding="utf-8-sig" if not exists else "utf-8",
    )


def record_profile(profile):
    exists = (
        OUTPUT_FILE.exists()
        and OUTPUT_FILE.stat().st_size > 0
    )

    pd.DataFrame([profile]).to_csv(
        OUTPUT_FILE,
        mode="a",
        header=not exists,
        index=False,
        encoding="utf-8-sig" if not exists else "utf-8",
    )


# =========================================
# 6. GOI API VA THU THAP PROFILE
# =========================================

processed = 0
stopped = False

for index, candidate in enumerate(candidates, start=1):
    login = candidate["login"]
    login_key = candidate["login_key"]
    activity_count = candidate["activity_count"]

    # Bo qua neu da co ket qua tu lan chay truoc
    if login_key in known_logins or login_key in finished_logins:
        continue

    url = f"https://api.github.com/users/{login}"

    print(
        f"\n[{index}/{len(candidates)}] {login} | "
        f"So lan xuat hien: {activity_count}"
    )

    user = None
    outcome = None

    for attempt in range(5):
        try:
            response = session.get(url, timeout=30)
        except requests.RequestException as error:
            print("Loi ket noi:", error)

            if attempt == 4:
                outcome = "connection_error"
                break

            time.sleep(15 * (attempt + 1))
            continue

        if response.status_code == 200:
            user = response.json()
            break

        if response.status_code == 404:
            outcome = "not_found"
            break

        body = response.text[:300].lower()

        is_limited = (
            response.status_code == 429
            or "rate limit" in body
            or bool(response.headers.get("Retry-After"))
            or response.headers.get("X-RateLimit-Remaining") == "0"
        )

        if response.status_code in (403, 429) and is_limited:
            retry_after = response.headers.get("Retry-After")

            if retry_after and retry_after.isdigit():
                wait = int(retry_after)
            else:
                wait = min(60 * (2 ** attempt), 900)

            print(f"GitHub gioi han API. Cho {wait} giay.")

            if attempt == 4:
                outcome = "rate_limited"
                break

            time.sleep(wait)
            continue

        print("Loi API:", response.status_code)
        print(response.text[:300])
        outcome = "api_error"
        break

    if outcome == "rate_limited":
        print("Tam dung de tranh tiep tuc khi bi gioi han.")
        stopped = True
        break

    if user is None:
        status = outcome or "request_failed"
        record_checkpoint(login, status, activity_count)

        if status == "not_found":
            finished_logins.add(login_key)
        else:
            print("Loi khac; se de lai de xu ly sau:", status)

        if status in ("connection_error", "api_error"):
            stopped = True
            break

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
        "followers": user.get("followers"),
        "following": user.get("following"),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
        "html_url": user.get("html_url"),
        "activity_count": activity_count,
    }

    # Luu profile truoc, checkpoint sau
    record_profile(profile)
    record_checkpoint(login, "ok", activity_count)

    known_logins.add(login_key)
    finished_logins.add(login_key)
    processed += 1

    print(
        f"Da luu: {login} | "
        f"Location: {user.get('location')}"
    )

    time.sleep(REQUEST_DELAY)


print("\n=== TONG KET ===")
print("Profile moi trong dot:", processed)
print("Profile da luu truoc do:", len(known_logins) - processed)
print("File profile bo sung:", OUTPUT_FILE)
print("Checkpoint:", CHECKPOINT_FILE)

if stopped:
    print("Da dung som; chay lai cung lenh de tiep tuc.")
