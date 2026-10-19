import pandas as pd

# =========================
# 1. ĐỌC DỮ LIỆU RAW
# =========================

repositories = pd.read_csv("repositories.csv")
issues = pd.read_csv("issues.csv")
commits = pd.read_csv("commits.csv")


# =========================
# 2. KIỂM TRA DỮ LIỆU
# =========================

print("===== DATA OVERVIEW =====")

print("\nRepositories:", repositories.shape)
print("Issues:", issues.shape)
print("Commits:", commits.shape)


# =========================
# 3. CHUYỂN KIỂU NGÀY
# =========================

repositories["created_at"] = pd.to_datetime(
    repositories["created_at"]
)

repositories["updated_at"] = pd.to_datetime(
    repositories["updated_at"]
)

issues["created_at"] = pd.to_datetime(
    issues["created_at"]
)

issues["closed_at"] = pd.to_datetime(
    issues["closed_at"]
)

commits["date"] = pd.to_datetime(
    commits["date"]
)


# =========================
# 4. XÓA DUPLICATE
# =========================

repositories = repositories.drop_duplicates()

issues = issues.drop_duplicates()

commits = commits.drop_duplicates()


# =========================
# 5. KIỂM TRA SAU CLEANING
# =========================

print("\n===== AFTER CLEANING =====")

print("\nRepositories:")
print(repositories.dtypes)

print("\nIssues:")
print(issues.dtypes)

print("\nCommits:")
print(commits.dtypes)


print("\nMissing values - Issues:")
print(issues.isnull().sum())


# =========================
# 6. LƯU DATA CLEAN
# =========================

repositories.to_csv(
    "repositories_clean.csv",
    index=False
)

issues.to_csv(
    "issues_clean.csv",
    index=False
)

commits.to_csv(
    "commits_clean.csv",
    index=False
)


print("\nĐã tạo dữ liệu sạch:")
print("- repositories_clean.csv")
print("- issues_clean.csv")
print("- commits_clean.csv")