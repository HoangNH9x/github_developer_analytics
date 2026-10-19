import requests
import pandas as pd
import os
from dotenv import load_dotenv

# Đọc GitHub Token từ file .env
load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")

headers = {
    "Authorization": f"Bearer {TOKEN}"
}


# Danh sách repository
repositories = [
    "facebook/react",
    "vuejs/vue",
    "angular/angular",
    "vercel/next.js",
    "django/django",
    "pallets/flask",
    "pytorch/pytorch",
    "tensorflow/tensorflow",
    "microsoft/vscode",
    "kubernetes/kubernetes"
]


commits_list = []

# Tổng số commit muốn lấy
MAX_COMMITS = 5000


# Lặp qua từng repository
for repo in repositories:

    print(f"\nĐang lấy Commits: {repo}")

    url = f"https://api.github.com/repos/{repo}/commits"

    repo_commit_count = 0

    # Mỗi page tối đa 100 commits
    for page in range(1, 6):

        # Nếu đã đủ 5000 commits thì dừng
        if len(commits_list) >= MAX_COMMITS:
            break

        params = {
            "per_page": 100,
            "page": page
        }

        response = requests.get(
            url,
            params=params,
            headers=headers
        )

        if response.status_code != 200:
            print(f"Lỗi {response.status_code}: {repo}")
            break

        data = response.json()

        # Nếu không còn dữ liệu
        if not data:
            break

        for commit in data:

            # GitHub user có thể không tồn tại hoặc không liên kết
            if commit["author"] is not None:
                author = commit["author"]["login"]
            else:
                author = commit["commit"]["author"]["name"]

            record = {
                "repository": repo,
                "sha": commit["sha"],
                "author": author,
                "message": commit["commit"]["message"],
                "date": commit["commit"]["author"]["date"]
            }

            commits_list.append(record)
            repo_commit_count += 1

        print(f"  Page {page}: {len(data)} commits")

    print(f"  Tổng commits của {repo}: {repo_commit_count}")


# Chuyển sang DataFrame
df = pd.DataFrame(commits_list)


# Hiển thị tổng số
print("\nTổng số Commits:", len(df))


# Hiển thị 5 dòng đầu
print("\n5 dòng đầu tiên:")
print(df.head())


# Lưu CSV
df.to_csv("commits.csv", index=False)

print("\nĐã lưu commits.csv")