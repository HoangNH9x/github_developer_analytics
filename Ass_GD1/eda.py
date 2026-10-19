import pandas as pd

# Đọc dữ liệu sạch
repositories = pd.read_csv("repositories_clean.csv")

print("===== REPOSITORY ANALYSIS =====")

# 1. Tổng số repository
print("\nTổng số repositories:", len(repositories))

# 2. Tổng số stars
print("Tổng số stars:", repositories["stars"].sum())

# 3. Tổng số forks
print("Tổng số forks:", repositories["forks"].sum())

# 4. Tổng số open issues
print("Tổng số open issues:", repositories["open_issues"].sum())

# 5. Ngôn ngữ lập trình
print("\nNgôn ngữ lập trình:")
print(repositories["language"].value_counts())

# 6. Repository có nhiều stars nhất
top_stars = repositories.sort_values(
    by="stars",
    ascending=False
)

print("\nTop repositories theo Stars:")
print(
    top_stars[
        ["repository", "stars", "forks", "language"]
    ].head(10)
)

# 7. Repository có nhiều forks nhất
top_forks = repositories.sort_values(
    by="forks",
    ascending=False
)

print("\nTop repositories theo Forks:")
print(
    top_forks[
        ["repository", "forks", "stars", "language"]
    ].head(10)
)

# 8. Repository có nhiều Open Issues nhất
top_issues = repositories.sort_values(
    by="open_issues",
    ascending=False
)

print("\nTop repositories theo Open Issues:")
print(
    top_issues[
        ["repository", "open_issues", "stars", "language"]
    ].head(10)
)



# =========================
# ISSUE ANALYSIS
# =========================

issues = pd.read_csv("issues_clean.csv")

print("\n\n===== ISSUE ANALYSIS =====")

# 1. Tổng số Issues
print("\nTổng số Issues:", len(issues))

# 2. Số lượng Open / Closed
print("\nTrạng thái Issues:")
print(issues["state"].value_counts())

# 3. Số Issues theo repository
issues_by_repo = issues["repository"].value_counts()

print("\nIssues theo Repository:")
print(issues_by_repo)

# 4. Tổng số comments
print("\nTổng số comments:", issues["comments"].sum())

# 5. Trung bình comments / Issue
print(
    "Trung bình comments / Issue:",
    round(issues["comments"].mean(), 2)
)

# 6. Repository có nhiều Issues nhất
print("\nTop repositories theo số Issues:")

top_issue_repos = (
    issues["repository"]
    .value_counts()
    .head(10)
)

print(top_issue_repos)

# 7. Top Issues có nhiều comments nhất
top_comments = issues.sort_values(
    by="comments",
    ascending=False
)

print("\nTop 10 Issues có nhiều comments nhất:")

print(
    top_comments[
        [
            "repository",
            "issue_number",
            "title",
            "state",
            "comments",
            "user"
        ]
    ].head(10)
)


# =========================
# COMMIT ANALYSIS
# =========================

commits = pd.read_csv("commits_clean.csv")

print("\n\n===== COMMIT ANALYSIS =====")

# 1. Tổng số commits
print("\nTổng số Commits:", len(commits))

# 2. Số commits theo repository
print("\nCommits theo Repository:")
print(
    commits["repository"]
    .value_counts()
)

# 3. Số lượng developer
print(
    "\nTổng số Developers:",
    commits["author"].nunique()
)

# 4. Top developers theo số commits
top_developers = (
    commits["author"]
    .value_counts()
    .head(10)
)

print("\nTop 10 Developers theo số Commit:")
print(top_developers)

# 5. Repository có nhiều commits nhất
top_commit_repos = (
    commits["repository"]
    .value_counts()
    .head(10)
)

print("\nTop repositories theo số Commits:")
print(top_commit_repos)

# 6. Developer đóng góp vào nhiều repository
developer_repos = (
    commits.groupby("author")["repository"]
    .nunique()
    .sort_values(ascending=False)
    .head(10)
)

print("\nTop Developers theo số Repository đóng góp:")
print(developer_repos)



# =========================
# HUMAN DEVELOPER ANALYSIS
# =========================

# Loại các tài khoản bot
human_commits = commits[
    ~commits["author"].str.endswith("[bot]", na=False)
]

print("\n\n===== HUMAN DEVELOPER ANALYSIS =====")

print(
    "\nTổng số commits của human developers:",
    len(human_commits)
)

print(
    "Tổng số human developers:",
    human_commits["author"].nunique()
)

print("\nTop 10 Human Developers theo số Commit:")

top_human_developers = (
    human_commits["author"]
    .value_counts()
    .head(10)
)

print(top_human_developers)


import matplotlib.pyplot as plt


# =========================
# 1. BIỂU ĐỒ STARS
# =========================

top_stars = repositories.sort_values(
    by="stars",
    ascending=True
)

plt.figure(figsize=(10, 6))

plt.barh(
    top_stars["repository"],
    top_stars["stars"]
)

plt.xlabel("Stars")
plt.ylabel("Repository")
plt.title("GitHub Repository Stars")

plt.tight_layout()

plt.savefig(
    "charts/stars_by_repo.png",
    dpi=300
)

plt.show()

# =========================
# 2. BIỂU ĐỒ ISSUES THEO REPOSITORY
# =========================

issues_by_repo = (
    issues["repository"]
    .value_counts()
    .sort_values(ascending=True)
)

plt.figure(figsize=(10, 6))

plt.barh(
    issues_by_repo.index,
    issues_by_repo.values
)

plt.xlabel("Number of Issues")
plt.ylabel("Repository")
plt.title("Issues by Repository")

plt.tight_layout()

plt.savefig(
    "charts/issues_by_repo.png",
    dpi=300
)

plt.show()


# =========================
# 3. BIỂU ĐỒ OPEN VS CLOSED ISSUES
# =========================

issue_status = issues["state"].value_counts()

plt.figure(figsize=(7, 7))

plt.pie(
    issue_status.values,
    labels=issue_status.index,
    autopct="%1.1f%%",
    startangle=90
)

plt.title("Open vs Closed Issues")

plt.tight_layout()

plt.savefig(
    "charts/issue_status.png",
    dpi=300
)

plt.show()


# =========================
# 4. TOP 10 DEVELOPERS THEO COMMITS
# =========================

top_developers = (
    commits["author"]
    .value_counts()
    .head(10)
    .sort_values(ascending=True)
)

plt.figure(figsize=(10, 6))

plt.barh(
    top_developers.index,
    top_developers.values
)

plt.xlabel("Number of Commits")
plt.ylabel("Developer")
plt.title("Top 10 Developers by Number of Commits")

plt.tight_layout()

plt.savefig(
    "charts/top_developers.png",
    dpi=300
)

plt.show()


# =========================
# 5. COMMITS THEO THỜI GIAN
# =========================

commits["date"] = pd.to_datetime(commits["date"])

commits_by_date = (
    commits
    .groupby(commits["date"].dt.date)
    .size()
)

plt.figure(figsize=(12, 6))

plt.plot(
    commits_by_date.index,
    commits_by_date.values
)

plt.xlabel("Date")
plt.ylabel("Number of Commits")
plt.title("GitHub Commits Over Time")

plt.xticks(rotation=45)

plt.tight_layout()

plt.savefig(
    "charts/commits_over_time.png",
    dpi=300
)

plt.show()