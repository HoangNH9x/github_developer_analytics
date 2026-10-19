
import os
import time
from pathlib import Path
import random

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

REPO_FILE = RAW / "repositories_stage2.csv"
COMMIT_FILE = RAW / "commits_stage2.csv"
ISSUE_FILE = RAW / "issues_stage2.csv"
PR_FILE = RAW / "pull_requests_stage2.csv"

OUTPUT_FILE = RAW / "developers_stage2.csv"
NOT_FOUND_FILE = RAW / "developers_not_found.csv"

REQUEST_DELAY = 1.2

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

session = requests.Session()
session.headers.update(headers)


# =========================================
# 2. THU THAP DANH SACH LOGIN
# =========================================

login_sources = {}


def add_login(login, source):
    if not isinstance(login, str):
        return

    login = login.strip()

    if not login or login.lower() in ("nan", "none", "null"):
        return

    key = login.lower()

    if key not in login_sources:
        login_sources[key] = {
            "login": login,
            "sources": set(),
        }

    login_sources[key]["sources"].add(source)


def read_logins(file_path, columns, source):
    if not file_path.exists():
        print(f"Chua co file: {file_path.name}")
        return

    try:
        df = pd.read_csv(
            file_path,
            encoding="utf-8-sig",
            dtype="string",
            usecols=lambda column: column in columns,
        )
    except (ValueError, pd.errors.EmptyDataError):
        print(f"Khong doc duoc cot can thiet: {file_path.name}")
        return

    for column in columns:
        if column not in df.columns:
            continue

        for login in df[column].dropna().unique():
            add_login(str(login), source)


print("Dang tao danh sach developer...")

read_logins(
    REPO_FILE,
    ["owner_login"],
    "repository_owner",
)

read_logins(
    COMMIT_FILE,
    ["author_login"],
    "commit_author",
)

read_logins(
    ISSUE_FILE,
    ["author_login"],
    "issue_author",
)

read_logins(
    PR_FILE,
    ["author_login", "merged_by"],
    "pull_request",
)

candidates = list(login_sources.values())

# Lay mau co the lap lai de phuc vu nghien cuu
random.Random(42).shuffle(candidates)

MAX_PROFILES = 3000
candidates = candidates[:MAX_PROFILES]

print("So Developer du kien lay mau:", len(candidates))


# =========================================
# 3. DOC CAC TAI KHOAN DA XU LY
# =========================================

def load_existing_logins(file_path):
    if not file_path.exists():
        return set()

    df = pd.read_csv(
        file_path,
        encoding="utf-8-sig",
        dtype="string",
    )

    if "login" not in df.columns:
        return set()

    return set(
        df["login"].dropna().str.lower()
    )


completed_logins = load_existing_logins(OUTPUT_FILE)
not_found_logins = load_existing_logins(NOT_FOUND_FILE)

print("Ho so da thu thap:", len(completed_logins))
print("Tai khoan khong tim thay da ghi nhan:", len(not_found_logins))


# =========================================
# 4. HAM GOI API CO THU LAI
# =========================================

def get_user(login):
    url = f"https://api.github.com/users/{login}"

    for attempt in range(5):
        try:
            response = session.get(
                url,
                timeout=30,
            )
        except requests.RequestException as error:
            print("Loi ket noi:", error)

            if attempt == 4:
                return None, "connection_error"

            wait_seconds = min(30 * (2 ** attempt), 900)
            print(f"Cho {wait_seconds} giay...")
            time.sleep(wait_seconds)
            continue

        if response.status_code == 200:
            return response.json(), None

        if response.status_code == 404:
            return None, "not_found"

        message = response.text[:300]
        lowered = message.lower()

        rate_limited = (
            response.status_code == 429
            or "rate limit" in lowered
            or bool(response.headers.get("Retry-After"))
            or response.headers.get("X-RateLimit-Remaining") == "0"
        )

        if response.status_code in (403, 429) and rate_limited:
            retry_after = response.headers.get("Retry-After")
            reset_at = response.headers.get("X-RateLimit-Reset")

            if retry_after and retry_after.isdigit():
                wait_seconds = int(retry_after)
            elif (
                response.headers.get("X-RateLimit-Remaining") == "0"
                and reset_at
            ):
                wait_seconds = max(
                    1,
                    int(reset_at) - int(time.time()),
                )
            else:
                wait_seconds = min(60 * (2 ** attempt), 900)

            if attempt == 4:
                print("Da thu lai toi da. Tam dung thu thap.")
                return None, "rate_limited"

            print(
                f"GitHub gioi han request. "
                f"Cho {wait_seconds} giay..."
            )
            time.sleep(wait_seconds)
            continue

        print(f"Loi API voi {login}: HTTP {response.status_code}")
        print(message)

        if response.status_code >= 500 and attempt < 4:
            time.sleep(min(10 * (2 ** attempt), 120))
            continue

        return None, f"http_{response.status_code}"

    return None, "request_failed"


# =========================================
# 5. THU THAP HO SO DEVELOPER
# =========================================

def append_row(file_path, record):
    file_exists = (
        file_path.exists()
        and file_path.stat().st_size > 0
    )

    pd.DataFrame([record]).to_csv(
        file_path,
        mode="a",
        header=not file_exists,
        index=False,
        encoding="utf-8-sig" if not file_exists else "utf-8",
    )


total = len(candidates)
processed = 0
stopped = False

for index, candidate in enumerate(candidates, start=1):
    login = candidate["login"]
    login_key = login.lower()

    if (
        login_key in completed_logins
        or login_key in not_found_logins
    ):
        continue

    print(f"\n[{index}/{total}] Dang lay ho so: {login}")

    user, error = get_user(login)

    if error == "not_found":
        append_row(
            NOT_FOUND_FILE,
            {
                "login": login,
                "reason": "404_not_found",
            },
        )
        not_found_logins.add(login_key)
        continue

    if error is not None:
        print("Tam dung de tranh mat tien do:", error)
        stopped = True
        break

    record = {
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
        "sources": "|".join(sorted(
            login_sources[login_key]["sources"]
        )),
    }

    append_row(OUTPUT_FILE, record)

    completed_logins.add(login_key)
    processed += 1

    print(
        f"Da luu ho so: {login} | "
        f"Loai tai khoan: {user.get('type')}"
    )

    time.sleep(REQUEST_DELAY)


# =========================================
# 6. TONG KET
# =========================================

print("\n=== TONG KET DEVELOPER ===")
print("Tong tai khoan trong danh sach:", total)
print("Ho so moi trong lan nay:", processed)
print("Tong ho so da luu:", len(completed_logins))
print("Tai khoan khong tim thay:", len(not_found_logins))
print("File developer:", OUTPUT_FILE)

if stopped:
    print("Da dung an toan. Chay lai sau khi API cho phep.")
