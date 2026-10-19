import requests
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

# Danh sách repository cần lấy Issues
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

issues_list = []

# Lặp qua từng repository
for repo in repositories:

    print(f"\nĐang lấy Issues: {repo}")

    url = f"https://api.github.com/repos/{repo}/issues"

    # Lấy tối đa 3 trang, mỗi trang 100 Issues
    issue_count = 0
    for page in range(1, 21):

        params = {
            "state": "all",
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

        # Nếu không còn dữ liệu thì dừng
        if not data:
            break

        for issue in data:

            # GitHub API trả cả Pull Request trong endpoint Issues
            # Nếu có pull_request thì bỏ qua
            if "pull_request" in issue:
                continue
            issue_count += 1

            record = {
                "repository": repo,
                "issue_number": issue["number"],
                "title": issue["title"],
                "state": issue["state"],
                "created_at": issue["created_at"],
                "closed_at": issue["closed_at"],
                "comments": issue["comments"],
                "user": issue["user"]["login"]
            }

            issues_list.append(record)

        print(f"  Page {page}: {len(data)} records")

 # Sau khi lấy xong tất cả các page của repository
    print(f"  Tổng Issues của {repo}: {issue_count}")


# Chuyển thành DataFrame
df = pd.DataFrame(issues_list)

# Hiển thị thông tin
print("\nTổng số Issues:", len(df))

print("\n5 dòng đầu tiên:")
print(df.head())

# Lưu CSV
df.to_csv("issues.csv", index=False)

print("\nĐã lưu issues.csv")