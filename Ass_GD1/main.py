import requests
import pandas as pd
import json

# Danh sách repository cần phân tích
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

repositories_list = []

for repo in repositories:

    url = f"https://api.github.com/repos/{repo}"

    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        print(json.dumps(data, indent=4, ensure_ascii=False))

    record = {
    "repository": data["full_name"],
    "owner": data["owner"]["login"],
    "stars": data["stargazers_count"],
    "forks": data["forks_count"],
    "open_issues": data["open_issues_count"],
    "language": data["language"],
    "created_at": data["created_at"],
    "updated_at": data["updated_at"]
}
    repositories_list.append(record)

    df = pd.DataFrame(repositories_list)

    df.to_csv("repositories.csv", index=False)