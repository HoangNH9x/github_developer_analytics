
import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# 1. Doc token tu file .env
load_dotenv()
token = os.getenv("GITHUB_TOKEN")

if not token:
    raise SystemExit("Khong tim thay GITHUB_TOKEN trong .env")

# 2. Doc danh sach repository da thu thap
repo_file = Path("data/raw/repositories_stage2.csv")

if not repo_file.exists():
    raise SystemExit("Khong tim thay file repository!")

repos_df = pd.read_csv(repo_file)

if repos_df.empty or "full_name" not in repos_df.columns:
    raise SystemExit("Danh sach repository khong hop le!")

# 3. Chon repository dau tien de thu nghiem
repo_name = repos_df.iloc[0]["full_name"]
owner, name = repo_name.split("/", 1)

print("Repository dang thu thap:", repo_name)

# 4. Goi GitHub API lay commit
url = f"https://api.github.com/repos/{owner}/{name}/commits"

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

params = {
    "since": "2020-01-01T00:00:00Z",
    "until": "2026-10-14T23:59:59Z",
    "per_page": 100,
    "page": 1
}

try:
    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30
    )

    print("HTTP Status:", response.status_code)

    if response.status_code == 200:
        items = response.json()
        commits = []

        for item in items:
            commit_data = item.get("commit") or {}
            author = item.get("author") or {}
            commit_author = commit_data.get("author") or {}
            committer = commit_data.get("committer") or {}

            commits.append({
                "repository": repo_name,
                "sha": item.get("sha"),
                "author_login": author.get("login"),
                "author_name": commit_author.get("name"),
                "author_date": commit_author.get("date"),
                "committer_date": committer.get("date"),
                "message": commit_data.get("message"),
                "html_url": item.get("html_url")
            })

        # 5. Luu file thu nghiem rieng
        output_dir = Path("data/raw")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "commits_test.csv"

        df = pd.DataFrame(commits)
        df.to_csv(
            output_file,
            index=False,
            encoding="utf-8-sig"
        )

        print("So commit thu duoc:", len(df))
        print("File da luu:", output_file)

        if not df.empty:
            print(df.head(5).to_string(index=False))

    else:
        print("Thong bao:", response.text[:500])

        if response.status_code in (403, 429):
            print("Dung thu thap; hay kiem tra gioi han API.")
        elif response.status_code == 404:
            print("Khong tim thay repository hoac endpoint.")

except requests.RequestException as error:
    print("Loi ket noi:", error)
