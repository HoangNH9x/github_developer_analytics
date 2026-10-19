
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

# Duong dan file
repo_file = Path("data/raw/repositories_stage2.csv")
test_file = Path("data/raw/commits_test.csv")
output_file = Path("data/raw/commits_stage2.csv")
progress_file = Path("data/raw/commits_repositories_done.csv")

if not repo_file.exists():
    raise SystemExit("Khong tim thay file repository!")

output_file.parent.mkdir(parents=True, exist_ok=True)

# Import 100 commit da thu nghiem vao bo du lieu chinh
seeded_repo = None

if not output_file.exists() and test_file.exists():
    test_df = pd.read_csv(test_file)

    if not test_df.empty:
        test_df.to_csv(
            output_file,
            index=False,
            encoding="utf-8-sig"
        )
        seeded_repo = str(test_df.iloc[0]["repository"])
        print("Da dua du lieu thu nghiem vao bo du lieu chinh.")

# Doc danh sach repo da hoan thanh
done_repos = set()

if progress_file.exists():
    done_df = pd.read_csv(progress_file)
    if "repository" in done_df.columns:
        done_repos = set(
            done_df["repository"].dropna().astype(str)
        )

# Neu vua nap du lieu thu nghiem, danh dau repo do da xu ly
if seeded_repo and seeded_repo not in done_repos:
    pd.DataFrame([{"repository": seeded_repo}]).to_csv(
        progress_file,
        mode="a",
        header=not progress_file.exists(),
        index=False,
        encoding="utf-8-sig"
    )
    done_repos.add(seeded_repo)

# Doc danh sach repository
repos_df = pd.read_csv(repo_file)
repo_names = (
    repos_df["full_name"]
    .dropna()
    .astype(str)
    .drop_duplicates()
    .tolist()
)

# Doc cac commit da luu de tranh ghi trung
seen_keys = set()

if output_file.exists():
    old_df = pd.read_csv(
        output_file,
        dtype={"repository": str, "sha": str}
    )

    if {"repository", "sha"}.issubset(old_df.columns):
        seen_keys = {
            f"{row.repository}|{row.sha}"
            for row in old_df[["repository", "sha"]].itertuples(
                index=False
            )
        }

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

batch_limit = 25
processed = 0
stop_collection = False

print("Tong repository:", len(repo_names))
print("Repository da hoan thanh:", len(done_repos))
print("Commit duy nhat da co:", len(seen_keys))

for repo_name in repo_names:
    if repo_name in done_repos:
        continue

    if processed >= batch_limit:
        print("Da hoan thanh mot dot 25 repository.")
        break

    owner, name = repo_name.split("/", 1)

    url = f"https://api.github.com/repos/{owner}/{name}/commits"

    params = {
        "since": "2020-01-01T00:00:00Z",
        "until": "2026-10-14T23:59:59Z",
        "per_page": 100,
        "page": 1
    }

    response = None

    # Thu toi da 2 lan neu bi gioi han request
    for attempt in range(2):
        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=30
            )
        except requests.RequestException as error:
            print("Loi ket noi:", error)
            response = None

        if response is not None and response.status_code == 200:
            break

        if response is not None and response.status_code == 404:
            print("Bo qua repository khong con truy cap:", repo_name)
            response = None
            break

        if response is not None and response.status_code not in (403, 429):
            print("Loi API:", response.status_code)
            print(response.text[:300])
            stop_collection = True
            break

        if attempt == 0:
            retry_after = (
                response.headers.get("Retry-After")
                if response is not None
                else None
            )

            wait_seconds = (
                int(retry_after) if retry_after else 60
            )

            print(
                f"API dang gioi han. Cho {wait_seconds} giay "
                f"truoc khi thu lai: {repo_name}"
            )
            time.sleep(wait_seconds)

    if stop_collection:
        break

    if response is None or response.status_code != 200:
        print("Tam dung. Du lieu da luu duoc giu nguyen.")
        break

    items = response.json()
    new_rows = []

    for item in items:
        sha = item.get("sha")
        if not sha:
            continue

        key = f"{repo_name}|{sha}"

        if key in seen_keys:
            continue

        commit_data = item.get("commit") or {}
        author_data = commit_data.get("author") or {}
        committer_data = commit_data.get("committer") or {}
        author_user = item.get("author") or {}

        new_rows.append({
            "repository": repo_name,
            "sha": sha,
            "author_login": author_user.get("login"),
            "author_name": author_data.get("name"),
            "author_date": author_data.get("date"),
            "committer_date": committer_data.get("date"),
            "message": commit_data.get("message"),
            "html_url": item.get("html_url")
        })

        seen_keys.add(key)

    if new_rows:
        pd.DataFrame(new_rows).to_csv(
            output_file,
            mode="a",
            header=not output_file.exists()
                or output_file.stat().st_size == 0,
            index=False,
            encoding="utf-8-sig"
        )

    # Ghi checkpoint sau khi luu commit
    pd.DataFrame([{"repository": repo_name}]).to_csv(
        progress_file,
        mode="a",
        header=not progress_file.exists(),
        index=False,
        encoding="utf-8-sig"
    )

    done_repos.add(repo_name)
    processed += 1

    print(
        f"[{processed}/{batch_limit}] {repo_name} | "
        f"Nhan {len(items)} commit | "
        f"Commit moi: {len(new_rows)}"
    )

    time.sleep(2)

print("\n=== KET QUA DOT NAY ===")
print("Repository xu ly trong dot:", processed)
print("Repository da hoan thanh:", len(done_repos))
print("Commit duy nhat da ghi:", len(seen_keys))
print("File commits:", output_file)
print("File checkpoint:", progress_file)
