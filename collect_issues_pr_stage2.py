
import os
import time
import shutil
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# ==================================================
# 1. CAU HINH
# ==================================================

load_dotenv()
token = os.getenv("GITHUB_TOKEN")

if not token:
    raise SystemExit("Khong tim thay GITHUB_TOKEN trong .env")

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"

REPO_FILE = RAW / "repositories_stage2.csv"
ISSUE_FILE = RAW / "issues_stage2.csv"
PR_FILE = RAW / "pull_requests_stage2.csv"
CHECKPOINT_FILE = RAW / "issues_pr_checkpoint.csv"
BACKUP_FILE = RAW / "issues_pr_checkpoint_backup.csv"

START_DATE = pd.Timestamp("2020-01-01", tz="UTC")
END_DATE = pd.Timestamp("2026-10-20 23:59:59", tz="UTC")

PER_PAGE = 100
REQUEST_DELAY = 1.5
MAX_PAGES_PER_REPO_PER_RUN = 3

if not REPO_FILE.exists():
    raise SystemExit("Khong tim thay repositories_stage2.csv")

RAW.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
})


# ==================================================
# 2. DOC ID DA THU THAP
# ==================================================

def load_seen_ids(file_path):
    if not file_path.exists():
        return set()

    df = pd.read_csv(
        file_path,
        encoding="utf-8-sig",
        dtype={"id": "string"},
    )

    if "id" not in df.columns:
        raise SystemExit(f"File thieu cot id: {file_path}")

    return set(df["id"].dropna().astype(str))


seen_issue_ids = load_seen_ids(ISSUE_FILE)
seen_pr_ids = load_seen_ids(PR_FILE)


def append_records(file_path, rows, seen_ids):
    new_rows = []

    for row in rows:
        record_id = str(row["id"])

        if record_id not in seen_ids:
            new_rows.append(row)
            seen_ids.add(record_id)

    if not new_rows:
        return 0

    need_header = (
        not file_path.exists()
        or file_path.stat().st_size == 0
    )

    pd.DataFrame(new_rows).to_csv(
        file_path,
        mode="a",
        header=need_header,
        index=False,
        encoding="utf-8-sig" if need_header else "utf-8",
    )

    return len(new_rows)


# ==================================================
# 3. DOC VA CHUYEN DOI CHECKPOINT CU
# ==================================================

repo_df = pd.read_csv(REPO_FILE)

repo_names = (
    repo_df["full_name"]
    .dropna()
    .astype(str)
    .drop_duplicates()
    .tolist()
)

states = {
    repo: {
        "issue_page": 1,
        "issue_next_url": "",
        "issue_done": False,
        "pr_page": 1,
        "pr_next_url": "",
        "pr_done": False,
    }
    for repo in repo_names
}

if CHECKPOINT_FILE.exists():
    old_cp = pd.read_csv(CHECKPOINT_FILE)

    cursor_schema = {
        "issue_next_url",
        "pr_next_url",
    }.issubset(old_cp.columns)

    # Bao luu checkpoint cu truoc khi chuyen doi
    if not cursor_schema and not BACKUP_FILE.exists():
        shutil.copy2(CHECKPOINT_FILE, BACKUP_FILE)
        print("Da sao luu checkpoint cu:", BACKUP_FILE)

    def as_bool(value):
        return str(value).strip().lower() in (
            "true", "1", "yes"
        )

    def as_url(value):
        if pd.isna(value):
            return ""
        value = str(value).strip()
        return "" if value.lower() in ("", "nan", "none") else value

    for _, row in old_cp.iterrows():
        repo = str(row["repository"])

        if repo not in states:
            continue

        state = states[repo]

        issue_page = max(1, int(row.get("issue_page", 1)))
        pr_page = max(1, int(row.get("pr_page", 1)))

        issue_done = as_bool(row.get("issue_done", False))
        pr_done = as_bool(row.get("pr_done", False))

        issue_next_url = (
            as_url(row["issue_next_url"])
            if cursor_schema else ""
        )
        pr_next_url = (
            as_url(row["pr_next_url"])
            if cursor_schema else ""
        )

        # Checkpoint cu chi luu so trang.
        # Lap lai trang thanh cong truoc do de lay Link cursor.
        if not cursor_schema:
            if not issue_done and issue_page > 1:
                issue_page -= 1

            if not pr_done and pr_page > 1:
                pr_page -= 1

        state.update({
            "issue_page": issue_page,
            "issue_next_url": issue_next_url,
            "issue_done": issue_done,
            "pr_page": pr_page,
            "pr_next_url": pr_next_url,
            "pr_done": pr_done,
        })


def save_checkpoint():
    rows = [
        {"repository": repo, **state}
        for repo, state in states.items()
    ]

    temp_file = CHECKPOINT_FILE.with_name(
        "issues_pr_checkpoint.tmp.csv"
    )

    pd.DataFrame(rows).to_csv(
        temp_file,
        index=False,
        encoding="utf-8-sig",
    )

    temp_file.replace(CHECKPOINT_FILE)


# ==================================================
# 4. GOI API VA XU LY RATE LIMIT
# ==================================================

def request_api(url, params=None):
    for attempt in range(6):
        try:
            response = session.get(
                url,
                params=params,
                timeout=30,
            )
        except requests.RequestException as error:
            print("Loi ket noi:", error)

            if attempt == 5:
                return None

            wait = min(30 * (2 ** attempt), 900)
            print(f"Thu lai sau {wait} giay...")
            time.sleep(wait)
            continue

        if response.status_code in (200, 404):
            return response

        message = response.text[:500]
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
                wait = int(retry_after)
            elif (
                response.headers.get("X-RateLimit-Remaining") == "0"
                and reset_at
            ):
                wait = max(1, int(reset_at) - int(time.time()))
            else:
                wait = min(60 * (2 ** attempt), 900)

            print(
                f"GitHub gioi han API: HTTP {response.status_code}"
            )

            if attempt == 5:
                print("Da thu lai toi da. Giu checkpoint va dung.")
                return None

            print(f"Cho {wait} giay...")
            time.sleep(wait)
            continue

        print("API loi:", response.status_code)
        print(message)
        return None

    return None


def get_next_url(response):
    # Theo Link header do GitHub tra ve, khong tu tang page
    link_header = response.headers.get("Link", "")

    for link in requests.utils.parse_header_links(link_header):
        if link.get("rel") == "next":
            return link.get("url", "")

    return ""


# ==================================================
# 5. TAO ROWS CHO ISSUES HOAC PULL REQUESTS
# ==================================================

def make_rows(repo, items, kind):
    rows = []
    found_older = False

    for item in items:
        created = pd.to_datetime(
            item.get("created_at"),
            utc=True,
            errors="coerce",
        )

        if pd.isna(created):
            continue

        if created < START_DATE:
            found_older = True
            continue

        if created > END_DATE:
            continue

        user = item.get("user") or {}

        if kind == "issue":
            # Endpoint Issues cung tra ve Pull Requests
            if "pull_request" in item:
                continue

            rows.append({
                "id": str(item.get("id")),
                "repository": repo,
                "number": item.get("number"),
                "title": item.get("title"),
                "state": item.get("state"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "closed_at": item.get("closed_at"),
                "author_login": user.get("login"),
                "author_association": item.get("author_association"),
                "comments": item.get("comments"),
                "labels": "|".join(
                    label.get("name", "")
                    for label in item.get("labels", [])
                    if isinstance(label, dict)
                ),
                "html_url": item.get("html_url"),
            })

        else:
            head = item.get("head") or {}
            base = item.get("base") or {}
            merged_by = item.get("merged_by") or {}

            rows.append({
                "id": str(item.get("id")),
                "repository": repo,
                "number": item.get("number"),
                "title": item.get("title"),
                "state": item.get("state"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "closed_at": item.get("closed_at"),
                "merged_at": item.get("merged_at"),
                "draft": item.get("draft"),
                "author_login": user.get("login"),
                "author_association": item.get("author_association"),
                "comments": item.get("comments"),
                "review_comments": item.get("review_comments"),
                "commits": item.get("commits"),
                "additions": item.get("additions"),
                "deletions": item.get("deletions"),
                "changed_files": item.get("changed_files"),
                "head_ref": head.get("ref"),
                "base_ref": base.get("ref"),
                "merged_by": merged_by.get("login"),
                "html_url": item.get("html_url"),
            })

    return rows, found_older


# ==================================================
# 6. THU THAP MOT LOAI DU LIEU THEO CURSOR
# ==================================================


def collect_stream(repo, kind):
    is_issue = kind == "issue"

    page_key = "issue_page" if is_issue else "pr_page"
    next_key = "issue_next_url" if is_issue else "pr_next_url"
    done_key = "issue_done" if is_issue else "pr_done"

    output_file = ISSUE_FILE if is_issue else PR_FILE
    seen_ids = seen_issue_ids if is_issue else seen_pr_ids

    owner, name = repo.split("/", 1)

    if is_issue:
        endpoint = (
            f"https://api.github.com/repos/{owner}/{name}/issues"
        )
    else:
        endpoint = (
            f"https://api.github.com/repos/{owner}/{name}/pulls"
        )

    state = states[repo]
    pages_this_run = 0

    while not state[done_key]:
        cursor_url = state[next_key]
        page = state[page_key]

        params = None

        if not cursor_url:
            params = {
                "state": "all",
                "sort": "created",
                "direction": "desc",
                "per_page": PER_PAGE,
            }

            if is_issue:
                params["since"] = "2020-01-01T00:00:00Z"
                params["filter"] = "all"

        request_url = cursor_url if cursor_url else endpoint

        response = request_api(
            request_url,
            params=params,
        )

        if response is None:
            print("Dung an toan, checkpoint da duoc giu.")
            return False

        if response.status_code == 404:
            print("Khong truy cap duoc repository:", repo)
            state[done_key] = True
            state[next_key] = ""
            save_checkpoint()
            return True

        items = response.json()

        if not isinstance(items, list):
            print("Du lieu API khong dung dinh dang:", repo, kind)
            return False

        if not items:
            state[done_key] = True
            state[next_key] = ""
            save_checkpoint()
            print(f"{kind} hoan tat: {repo}")
            break

        rows, found_older = make_rows(repo, items, kind)

        added = append_records(
            output_file,
            rows,
            seen_ids,
        )

        next_url = get_next_url(response)

        state[page_key] = page + 1

        if found_older or not next_url:
            state[done_key] = True
            state[next_key] = ""
        else:
            state[next_key] = next_url

        save_checkpoint()

        print(
            f"{kind.upper()} | {repo} | "
            f"Trang theo doi {page} | "
            f"Nhan {len(items)} item | "
            f"Moi them {added}"
        )

        pages_this_run += 1

        if state[done_key]:
            print(f"{kind} hoan tat: {repo}")
            break

        if pages_this_run >= MAX_PAGES_PER_REPO_PER_RUN:
            print(
                f"Tam dung {kind} tai {repo} sau "
                f"{pages_this_run} trang. "
                "Checkpoint da duoc luu."
            )
            return True

        time.sleep(REQUEST_DELAY)

    return True




# ==================================================
# 7. CHAY TU DONG VA LUU CHECKPOINT
# ==================================================

print("Tong repository:", len(repo_names))
print("Issues da co:", len(seen_issue_ids))
print("Pull Requests da co:", len(seen_pr_ids))
print("Bat dau tiep tuc tu checkpoint...\n")

stopped = False

try:
    for index, repo in enumerate(repo_names, start=1):
        state = states[repo]

        if state["issue_done"] and state["pr_done"]:
            continue

        print(f"\n[{index}/{len(repo_names)}] {repo}")

        if not state["issue_done"]:
            if not collect_stream(repo, "issue"):
                stopped = True
                break

        if not state["pr_done"]:
            if not collect_stream(repo, "pr"):
                stopped = True
                break

        time.sleep(REQUEST_DELAY)

except KeyboardInterrupt:
    stopped = True
    print("\nDa nhan lenh dung tu ban phim.")

finally:
    save_checkpoint()

completed = sum(
    1 for state in states.values()
    if state["issue_done"] and state["pr_done"]
)

print("\n=== TONG KET ===")
print("Repository hoan tat ca hai loai:", completed)
print("Tong repository:", len(repo_names))
print("Issues da luu:", len(seen_issue_ids))
print("Pull Requests da luu:", len(seen_pr_ids))
print("File Issues:", ISSUE_FILE)
print("File Pull Requests:", PR_FILE)
print("Checkpoint:", CHECKPOINT_FILE)

if stopped:
    print("Da dung som; du lieu va checkpoint duoc giu lai.")
