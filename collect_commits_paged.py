
import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# ==========================================
# 1. CAU HINH
# ==========================================

load_dotenv()
token = os.getenv("GITHUB_TOKEN")

if not token:
    raise SystemExit("Khong tim thay GITHUB_TOKEN trong file .env")

repo_file = Path("data/raw/repositories_stage2.csv")
output_file = Path("data/raw/commits_stage2.csv")
checkpoint_file = Path("data/raw/commits_pagination_checkpoint.csv")

PER_PAGE = 100

# Gioi han moi lan chay de tranh gui qua nhieu request
MAX_REPOS_PER_RUN = 5
MAX_PAGES_PER_REPO_PER_RUN = 5
REQUEST_DELAY = 2

if not repo_file.exists():
    raise SystemExit("Khong tim thay repositories_stage2.csv")

output_file.parent.mkdir(parents=True, exist_ok=True)

# ==========================================
# 2. DOC DANH SACH REPOSITORY
# ==========================================

repos_df = pd.read_csv(repo_file)

repo_names = (
    repos_df["full_name"]
    .dropna()
    .astype(str)
    .drop_duplicates()
    .tolist()
)

print("Tong repository:", len(repo_names))

# ==========================================
# 3. DOC COMMITS DA CO
# ==========================================

seen_keys = set()
repo_counts = {}

if output_file.exists():
    old_df = pd.read_csv(
        output_file,
        encoding="utf-8-sig",
        dtype={"repository": str, "sha": str}
    )

    required = {"repository", "sha"}

    if not required.issubset(old_df.columns):
        raise SystemExit(
            "File commits hien tai thieu cot repository hoac sha."
        )

    valid_df = old_df.dropna(subset=["repository", "sha"])

    seen_keys = {
        (str(repo), str(sha))
        for repo, sha in zip(
            valid_df["repository"],
            valid_df["sha"]
        )
    }

    repo_counts = (
        valid_df.groupby("repository")["sha"]
        .nunique()
        .to_dict()
    )

print("Commit duy nhat da co:", len(seen_keys))

# ==========================================
# 4. KHOI TAO CHECKPOINT
# ==========================================

def initial_state(repo):
    count = int(repo_counts.get(repo, 0))

    if count >= PER_PAGE:
        # Du lieu cu co trang dau 100 commit.
        # Tiep tuc thu tu trang 2.
        return {
            "next_page": 2,
            "completed": False
        }

    if count > 0:
        # Luot thu nghiem truoc chi nhan duoi 100 ket qua.
        return {
            "next_page": 2,
            "completed": True
        }

    return {
        "next_page": 1,
        "completed": False
    }


states = {
    repo: initial_state(repo)
    for repo in repo_names
}

# Neu da co checkpoint moi, khoi phuc tien do
if checkpoint_file.exists():
    checkpoint_df = pd.read_csv(checkpoint_file)

    for _, row in checkpoint_df.iterrows():
        repo = str(row["repository"])

        if repo not in states:
            continue

        states[repo] = {
            "next_page": max(1, int(row["next_page"])),
            "completed": str(row["completed"]).lower()
            in ("true", "1", "yes")
        }

def save_checkpoint():
    rows = []

    for repo, state in states.items():
        rows.append({
            "repository": repo,
            "next_page": state["next_page"],
            "completed": state["completed"]
        })

    pd.DataFrame(rows).to_csv(
        checkpoint_file,
        index=False,
        encoding="utf-8-sig"
    )

# Tao checkpoint lan dau
save_checkpoint()

# ==========================================
# 5. KET NOI GITHUB API
# ==========================================

session = requests.Session()

session.headers.update({
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
})

def fetch_page(url, params):
    for attempt in range(3):
        try:
            response = session.get(
                url,
                params=params,
                timeout=30
            )
        except requests.RequestException as error:
            print("Loi ket noi:", error)

            if attempt == 2:
                return None

            wait_seconds = 30 * (2 ** attempt)
            print(f"Thu lai sau {wait_seconds} giay...")
            time.sleep(wait_seconds)
            continue

        if response.status_code == 200:
            return response

        if response.status_code in (403, 429):
            retry_after = response.headers.get("Retry-After")
            remaining = response.headers.get(
                "X-RateLimit-Remaining"
            )
            reset = response.headers.get("X-RateLimit-Reset")

            if retry_after and retry_after.isdigit():
                wait_seconds = int(retry_after)
            elif remaining == "0" and reset:
                wait_seconds = max(
                    1, int(reset) - int(time.time())
                )
            else:
                wait_seconds = 60 * (2 ** attempt)

            print(
                f"GitHub gioi han request: "
                f"HTTP {response.status_code}"
            )

            if attempt == 2:
                print("Tam dung va giu nguyen checkpoint.")
                return None

            print(f"Cho {wait_seconds} giay...")
            time.sleep(wait_seconds)
            continue

        print("API loi:", response.status_code)
        print(response.text[:300])
        return None

    return None

# ==========================================
# 6. THU THAP COMMITS THEO PHAN TRANG
# ==========================================

processed_repos = 0
stop_collection = False

for repo in repo_names:
    state = states[repo]

    if state["completed"]:
        continue

    if processed_repos >= MAX_REPOS_PER_RUN:
        break

    processed_repos += 1

    owner, name = repo.split("/", 1)
    url = f"https://api.github.com/repos/{owner}/{name}/commits"

    print(f"\nRepository: {repo}")

    for page_attempt in range(MAX_PAGES_PER_REPO_PER_RUN):
        page = state["next_page"]

        params = {
            "since": "2020-01-01T00:00:00Z",
            "until": "2026-10-14T23:59:59Z",
            "per_page": PER_PAGE,
            "page": page
        }

        response = fetch_page(url, params)

        if response is None:
            stop_collection = True
            break

        if response.status_code == 404:
            print("Repository khong truy cap duoc:", repo)
            state["completed"] = True
            save_checkpoint()
            break

        items = response.json()

        if not isinstance(items, list):
            print("API khong tra ve danh sach commit.")
            stop_collection = True
            break

        new_rows = []

        for item in items:
            sha = item.get("sha")

            if not sha:
                continue

            key = (repo, str(sha))

            if key in seen_keys:
                continue

            commit_data = item.get("commit") or {}
            author_data = commit_data.get("author") or {}
            committer_data = commit_data.get("committer") or {}
            author_user = item.get("author") or {}

            new_rows.append({
                "repository": repo,
                "sha": sha,
                "author_login": author_user.get("login"),
                "author_name": author_data.get("name"),
                "author_date": author_data.get("date"),
                "committer_date": committer_data.get("date"),
                "message": commit_data.get("message"),
                "html_url": item.get("html_url")
            })

            seen_keys.add(key)

        # Luu commits truoc khi cap nhat checkpoint
        if new_rows:
            header_needed = (
                not output_file.exists()
                or output_file.stat().st_size == 0
            )

            pd.DataFrame(new_rows).to_csv(
                output_file,
                mode="a",
                header=header_needed,
                index=False,
                encoding=(
                    "utf-8-sig" if header_needed else "utf-8"
                )
            )

        # Cap nhat trang tiep theo
        state["next_page"] = page + 1

        # Trang it hon 100 ket qua nghia la het du lieu
        if len(items) < PER_PAGE:
            state["completed"] = True

        save_checkpoint()

        print(
            f"Trang {page}: nhan {len(items)} commit | "
            f"Commit moi {len(new_rows)} | "
            f"Tong duy nhat {len(seen_keys)}"
        )

        if state["completed"]:
            print("Da thu thap het commits cua repository nay.")
            break

        time.sleep(REQUEST_DELAY)

    if stop_collection:
        break

    time.sleep(REQUEST_DELAY)

# ==========================================
# 7. TONG KET
# ==========================================

completed_count = sum(
    1 for state in states.values()
    if state["completed"]
)

print("\n=== KET QUA DOT THU THAP ===")
print("Repository xu ly trong dot:", processed_repos)
print("Repository da hoan tat:", completed_count)
print("Repository con dang cho:", len(states) - completed_count)
print("Commit duy nhat da biet:", len(seen_keys))
print("File commits:", output_file)
print("Checkpoint:", checkpoint_file)

if stop_collection:
    print("Da dung an toan. Co the chay lai sau.")
