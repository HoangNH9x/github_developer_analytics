
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

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

url = "https://api.github.com/search/repositories"
output_file = Path("data/raw/repositories_stage2.csv")
output_file.parent.mkdir(parents=True, exist_ok=True)

# Doc du lieu da luu de khong phai bat dau lai tu dau
repositories = {}

if output_file.exists():
    old_df = pd.read_csv(output_file)

    for item in old_df.to_dict(orient="records"):
        repo_id = str(item["repo_id"])
        repositories[repo_id] = item

print("Repository da co:", len(repositories))

# Moi truy van tim kiem chi lay toi da 1000 ket qua
start_page = len(repositories) // 100 + 1
last_page = min(10, 1000 // 100)
total_count = 0
stop_collection = False

params = {
    "q": "created:2020-01-01..2026-10-14",
    "sort": "stars",
    "order": "desc",
    "per_page": 100
}

if len(repositories) >= 1000:
    print("Da dat muc thu nghiem 1000 repository.")
else:
    for page in range(start_page, last_page + 1):
        params["page"] = page
        response = None

        # Toi da 4 lan thu cho moi trang
        for attempt in range(4):
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=30
                )
            except requests.RequestException as error:
                print("Loi ket noi:", error)

                if attempt == 3:
                    stop_collection = True
                    break

                wait_seconds = 60 * (2 ** attempt)
                print(f"Thu lai sau {wait_seconds} giay...")
                time.sleep(wait_seconds)
                continue

            if response.status_code == 200:
                break

            if response.status_code in (403, 429):
                retry_after = response.headers.get("Retry-After")
                remaining = response.headers.get("X-RateLimit-Remaining")
                reset = response.headers.get("X-RateLimit-Reset")

                if retry_after:
                    wait_seconds = int(retry_after)
                elif remaining == "0" and reset:
                    wait_seconds = max(1, int(reset) - int(time.time()))
                else:
                    wait_seconds = 60 * (2 ** attempt)

                print("GitHub dang gioi han request.")
                print("HTTP Status:", response.status_code)

                if attempt == 3:
                    print("Da het so lan thu lai. Dung an toan.")
                    stop_collection = True
                    break

                print(f"Se thu lai sau {wait_seconds} giay.")
                time.sleep(wait_seconds)
                continue

            print("API loi:", response.status_code)
            print(response.text[:300])
            stop_collection = True
            break

        if stop_collection:
            break

        if response is None or response.status_code != 200:
            break

        result = response.json()
        total_count = result.get("total_count", total_count)
        items = result.get("items", [])

        if not items:
            print("Khong con du lieu.")
            break

        for item in items:
            repo_id = str(item["id"])

            repositories[repo_id] = {
                "repo_id": item.get("id"),
                "full_name": item.get("full_name"),
                "owner_login": item.get("owner", {}).get("login"),
                "owner_type": item.get("owner", {}).get("type"),
                "description": item.get("description"),
                "language": item.get("language"),
                "stars": item.get("stargazers_count"),
                "forks": item.get("forks_count"),
                "open_issues": item.get("open_issues_count"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "pushed_at": item.get("pushed_at"),
                "html_url": item.get("html_url")
            }

        # Luu sau moi trang thanh cong
        df = pd.DataFrame(list(repositories.values()))
        df = df.drop_duplicates(subset=["repo_id"])
        df.to_csv(output_file, index=False, encoding="utf-8-sig")

        print(
            f"Trang {page}: nhan {len(items)} repository | "
            f"Tong da luu: {len(df)}"
        )

        if len(items) < 100:
            break

        time.sleep(2)

print("\n=== KET QUA ===")
print("Tong ket qua khop truy van:", total_count)
print("Tong repository da luu:", len(repositories))
print("File:", output_file)

if stop_collection:
    print("Da dung an toan. Chay lai sau khi het gioi han API.")
