"""Canonical repository-centric crawl, transform and quality audit CLI.

This is the only intended entry point for the rebuilt Final data pipeline.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

from .config import (
    DATA_DIR, DEFAULT_STUDY_END, DEFAULT_STUDY_START, PROCESSED_DIR, RAW_DIR, Settings,
)
from .country import resolve_country
from .github_api import GitHubAPIError, GitHubClient

CANONICAL_RAW = RAW_DIR / "canonical"
CANONICAL_PROCESSED = PROCESSED_DIR / "canonical"
CHECKPOINT_PATH = CANONICAL_RAW / "repository_checkpoint.csv"
SEED_PATH = RAW_DIR / "repositories_stage2.csv"

COMMIT_COLUMNS = [
    "repository_id", "full_name", "commit_sha", "author_login", "author_name",
    "author_date", "committer_date", "commit_message", "html_url", "collected_at",
]
ISSUE_COLUMNS = [
    "repository_id", "full_name", "issue_id", "issue_number", "title", "created_at",
    "updated_at", "closed_at", "state", "comments_count", "html_url", "collected_at",
]
PR_COLUMNS = [
    "repository_id", "full_name", "pr_id", "pr_number", "title", "created_at",
    "updated_at", "closed_at", "merged_at", "state", "comments_count", "html_url",
    "collected_at",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_append(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(dict.fromkeys(k for row in rows for k in row.keys()))
    file_exists = path.exists() and path.stat().st_size > 0
    # utf-8-sig is used only when creating a file, avoiding a BOM in appended chunks.
    with path.open("a" if file_exists else "w", encoding="utf-8-sig" if not file_exists else "utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def write_frame(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def read_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def upsert_by_key(path: Path, new_rows: list[dict[str, Any]], key: str) -> None:
    if not new_rows:
        return
    old = read_csv_if_exists(path)
    incoming = pd.DataFrame(new_rows)
    combined = pd.concat([old, incoming], ignore_index=True, sort=False)
    if key in combined.columns:
        combined = combined.drop_duplicates(subset=[key], keep="last")
    write_frame(path, combined)


def read_seed(path: Path, limit: int | None = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy danh sách repository: {path}. "
            "Hãy cung cấp --seed hoặc đặt repositories_stage2.csv trong data/raw/."
        )
    seed = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    name_col = next((col for col in ["full_name", "repo_full_name", "repository_full_name"] if col in seed), None)
    if name_col is None:
        if {"owner_login", "name"}.issubset(seed.columns):
            seed["full_name"] = seed["owner_login"].astype(str) + "/" + seed["name"].astype(str)
            name_col = "full_name"
        else:
            raise ValueError("Seed cần có cột full_name hoặc cặp owner_login + name.")
    seed["full_name"] = seed[name_col].astype(str).str.strip()
    seed = seed[seed["full_name"].str.contains("/", regex=False) & seed["full_name"].ne("nan")].copy()
    seed = seed.drop_duplicates(subset=["full_name"], keep="first")
    if "sample_source" not in seed:
        seed["sample_source"] = "global_seed"
    seed["sample_source"] = seed["sample_source"].fillna("global_seed")
    if limit is not None:
        seed = seed.head(max(0, limit))
    return seed.reset_index(drop=True)


def discover_global_repositories(
    client: GitHubClient,
    repository_limit: int,
    per_country_limit: int,
    min_stars: int = 50,
    max_stars: int = 5000,
    excluded_full_names: set[str] | None = None,
    excluded_owners: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Discover a small, stratified sample with recognized non-Vietnam owner countries.

    This is a purposive comparison sample, not a random or globally representative sample.
    It caps repositories per owner-country and filters self-reported public owner locations.
    """
    if repository_limit <= 0:
        return []
    if min_stars < 0 or max_stars < min_stars:
        raise ValueError("Invalid global star range.")

    languages = ["Python", "JavaScript", "TypeScript", "Go", "Java", "Rust"]
    excluded_names = {name.lower() for name in (excluded_full_names or set())}
    excluded_owner_logins = {name.lower() for name in (excluded_owners or set())}
    candidates: dict[str, dict[str, Any]] = {}

    print(
        f"[INFO] Tìm mẫu quốc tế: stars {min_stars}..{max_stars}, "
        f"tối đa {repository_limit} repo, tối đa {per_country_limit} repo/quốc gia.",
        flush=True,
    )
    for language in languages:
        query = f"stars:{min_stars}..{max_stars} is:public fork:false language:{language}"
        try:
            payload, _ = client.request_json(
                "search/repositories",
                {"q": query, "sort": "stars", "order": "desc", "per_page": 100, "page": 1},
            )
            if not isinstance(payload, dict):
                continue
            items = payload.get("items", [])
            print(
                f"[INFO] Global discovery {language}: {len(items)} candidates fetched.",
                flush=True,
            )
            for item in items:
                full_name = str(item.get("full_name") or "").strip()
                owner = item.get("owner") or {}
                login = str(owner.get("login") or "").strip()
                repo_id = item.get("id")
                if not full_name or not login or not repo_id:
                    continue
                if full_name.lower() in excluded_names or login.lower() in excluded_owner_logins:
                    continue
                if item.get("private") or item.get("fork"):
                    continue
                current = candidates.get(full_name.lower())
                if current is None or int(item.get("stargazers_count") or 0) > int(current.get("stargazers_count") or 0):
                    candidates[full_name.lower()] = item
        except Exception as exc:
            print(f"[WARN] Global repository search failed for {language}: {exc}", file=sys.stderr)

    ordered = sorted(
        candidates.values(),
        key=lambda row: int(row.get("stargazers_count") or 0),
        reverse=True,
    )
    owner_cache: dict[str, tuple[dict[str, Any] | None, str | None]] = {}
    owner_used: set[str] = set(excluded_owner_logins)
    country_counts: Counter[str] = Counter()
    selected: list[dict[str, Any]] = []

    for index, repo in enumerate(ordered, start=1):
        full_name = str(repo.get("full_name") or "")
        owner = repo.get("owner") or {}
        login = str(owner.get("login") or "").strip()
        owner_type = owner.get("type")
        if not login or login.lower() in owner_used:
            continue

        if login.lower() not in owner_cache:
            try:
                profile = client.owner_profile(login, owner_type)
                country = resolve_country(profile.get("location"))
                owner_cache[login.lower()] = (profile, country)
            except Exception as exc:
                print(f"[WARN] Global owner profile unavailable for {login}: {exc}", file=sys.stderr)
                owner_cache[login.lower()] = (None, None)

        profile, country = owner_cache[login.lower()]
        if not profile or not country or country == "Vietnam":
            continue
        if country_counts[country] >= per_country_limit:
            continue

        selected.append({
            "repository_id": repo.get("id"),
            "full_name": full_name,
            "sample_source": "global_owner_discovery",
        })
        owner_used.add(login.lower())
        country_counts[country] += 1
        print(
            f"[SAMPLE] Global repo {len(selected)}/{repository_limit}: "
            f"{full_name} — owner country {country}.",
            flush=True,
        )
        if len(selected) >= repository_limit:
            break

    print(
        f"[INFO] Global owner-country sample selected: {len(selected)} repositories; "
        f"recognized countries={dict(country_counts)}.",
        flush=True,
    )
    return selected


def discover_vietnam_repositories(
    client: GitHubClient, owner_limit: int, repos_per_owner: int
) -> list[dict[str, Any]]:
    """Opt-in discovery; public location must resolve to Vietnam before a repository is included."""
    candidate_queries = [
        "location:Vietnam type:user",
        "location:Hanoi type:user",
        'location:"Ho Chi Minh City" type:user',
        "location:Danang type:user",
        "location:Vietnam type:org",
        "location:Hanoi type:org",
        'location:"Ho Chi Minh City" type:org',
    ]
    owners: dict[str, dict[str, Any]] = {}
    for query in candidate_queries:
        try:
            payload, _ = client.request_json("search/users", {"q": query, "per_page": 100, "page": 1})
            if not isinstance(payload, dict):
                continue
            for item in payload.get("items", []):
                login = item.get("login")
                if login:
                    owners[str(login).lower()] = item
        except Exception as exc:
            print(f"[WARN] Search Vietnam owners query failed ({query}): {exc}", file=sys.stderr)

    verified: list[tuple[str, dict[str, Any]]] = []
    for login in sorted(owners):
        try:
            profile = client.owner_profile(login)
            location = profile.get("location")
            if resolve_country(location) == "Vietnam":
                verified.append((login, profile))
        except Exception:
            continue
        if len(verified) >= owner_limit:
            break

    repositories: dict[str, dict[str, Any]] = {}
    for login, profile in verified:
        owner_type = profile.get("type") or owners[login].get("type") or "User"
        # Repository search supports star sorting; the per-owner list endpoint does not.
        owner_qualifier = "org" if str(owner_type).lower() == "organization" else "user"
        try:
            payload, _ = client.request_json(
                "search/repositories",
                {"q": f"{owner_qualifier}:{login} is:public", "sort": "stars", "order": "desc", "per_page": 100, "page": 1},
            )
            if not isinstance(payload, dict):
                continue
            rows = payload.get("items", [])
        except Exception as exc:
            print(f"[WARN] Could not search repos for Vietnam owner {login}: {exc}", file=sys.stderr)
            continue
        included = 0
        for repo in rows:
            if repo.get("private") or repo.get("fork"):
                continue
            full_name = repo.get("full_name")
            repo_id = repo.get("id")
            if not full_name or not repo_id:
                continue
            repositories[str(full_name).lower()] = {
                "repository_id": repo_id,
                "full_name": full_name,
                "sample_source": "vietnam_owner_discovery",
            }
            included += 1
            if included >= repos_per_owner:
                break
    return list(repositories.values())


def normalize_commit(repo_id: Any, full_name: str, item: dict[str, Any], collected_at: str) -> dict[str, Any]:
    commit = item.get("commit") or {}
    author = commit.get("author") or {}
    committer = commit.get("committer") or {}
    account = item.get("author") or {}
    return {
        "repository_id": repo_id,
        "full_name": full_name,
        "commit_sha": item.get("sha"),
        "author_login": account.get("login"),
        "author_name": author.get("name"),
        "author_date": author.get("date"),
        "committer_date": committer.get("date"),
        "commit_message": commit.get("message"),
        "html_url": item.get("html_url"),
        "collected_at": collected_at,
    }


def normalize_issue(repo_id: Any, full_name: str, item: dict[str, Any], collected_at: str) -> dict[str, Any]:
    return {
        "repository_id": repo_id,
        "full_name": full_name,
        "issue_id": item.get("id"),
        "issue_number": item.get("number"),
        "title": item.get("title"),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "closed_at": item.get("closed_at"),
        "state": item.get("state"),
        "comments_count": item.get("comments"),
        "creator_login": (item.get("user") or {}).get("login"),
        "creator_type": (item.get("user") or {}).get("type"),
        "html_url": item.get("html_url"),
        "collected_at": collected_at,
    }


def normalize_pr(repo_id: Any, full_name: str, item: dict[str, Any], collected_at: str) -> dict[str, Any]:
    return {
        "repository_id": repo_id,
        "full_name": full_name,
        "pr_id": item.get("id"),
        "pr_number": item.get("number"),
        "title": item.get("title"),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "closed_at": item.get("closed_at"),
        "merged_at": item.get("merged_at"),
        "state": item.get("state"),
        "comments_count": item.get("comments"),
        "creator_login": (item.get("user") or {}).get("login"),
        "creator_type": (item.get("user") or {}).get("type"),
        "html_url": item.get("html_url"),
        "collected_at": collected_at,
    }


def collect_one(
    client: GitHubClient,
    seed_row: dict[str, Any],
    settings: Settings,
    previous_checkpoint: dict[str, Any] | None = None,
    reuse_complete_metrics: bool = True,
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    full_name = str(seed_row["full_name"])
    collected_at = utc_now()
    source = seed_row.get("sample_source") or "global_seed"
    try:
        repo = client.get_one(f"repos/{full_name}")
    except Exception as exc:
        base = {
            "repository_id": seed_row.get("repository_id", seed_row.get("repo_id")),
            "full_name": full_name,
            "repo_name": full_name.split("/", 1)[-1],
            "owner_login": seed_row.get("owner_login", full_name.split("/", 1)[0]),
            "owner_type": seed_row.get("owner_type"),
            "owner_profile_location": None,
            "owner_country": None,
            "owner_country_status": "UNKNOWN",
            "stars_snapshot": None,
            "forks_snapshot": None,
            "open_issues_count_api_includes_pr": None,
            "sample_source": source,
            "snapshot_at": collected_at,
            "collected_at": collected_at,
            "metadata_status": "ERROR",
            "metadata_error": str(exc),
            "study_start": settings.study_start,
            "study_end": settings.study_end,
        }
        checkpoint = {
            "full_name": full_name, "repository_id": base["repository_id"],
            "commits_status": "NOT_RUN", "issues_status": "NOT_RUN", "prs_status": "NOT_RUN",
            "metadata_status": "ERROR", "error": str(exc), "collected_at": collected_at,
            "study_start": settings.study_start, "study_end": settings.study_end,
        }
        return base, None, checkpoint, [], [], []

    print(
        f"[OK] Metadata {repo.get('full_name') or full_name}: "
        f"stars={repo.get('stargazers_count')}, forks={repo.get('forks_count')}",
        flush=True,
    )
    repository_id = repo.get("id")
    owner = repo.get("owner") or {}
    owner_login = owner.get("login") or full_name.split("/", 1)[0]
    owner_type = owner.get("type")
    profile: dict[str, Any] | None = None
    profile_error = None
    print(f"[PHASE] Đang lấy public profile của owner {owner_login}...", flush=True)
    try:
        profile = client.owner_profile(owner_login, owner_type)
    except Exception as exc:
        profile_error = str(exc)
    raw_location = profile.get("location") if profile else None
    print(
        f"[PHASE] Owner profile: {'OK' if profile else 'ERROR'}; "
        f"location={raw_location or 'không công khai'}",
        flush=True,
    )
    owner_country = resolve_country(raw_location)
    meta = {
        "repository_id": repository_id,
        "full_name": repo.get("full_name") or full_name,
        "repo_name": repo.get("name"),
        "owner_login": owner_login,
        "owner_type": owner_type,
        "owner_profile_location": raw_location,
        "owner_country": owner_country,
        "owner_country_status": "RECOGNIZED" if owner_country else "UNKNOWN",
        "description": repo.get("description"),
        "language": repo.get("language"),
        "stars_snapshot": repo.get("stargazers_count"),
        "forks_snapshot": repo.get("forks_count"),
        "open_issues_count_api_includes_pr": repo.get("open_issues_count"),
        "created_at": repo.get("created_at"),
        "updated_at": repo.get("updated_at"),
        "pushed_at": repo.get("pushed_at"),
        "html_url": repo.get("html_url"),
        "sample_source": source,
        "snapshot_at": collected_at,
        "metadata_status": "COMPLETE",
        "owner_profile_status": "COMPLETE" if profile else "ERROR",
        "owner_profile_error": profile_error,
        "study_start": settings.study_start,
        "study_end": settings.study_end,
    }

    prev = previous_checkpoint or {}
    same_window = (
        str(prev.get("study_start")) == settings.study_start
        and str(prev.get("study_end")) == settings.study_end
    )

    def reusable(metric: str, raw_path: Path) -> bool:
        status = prev.get(f"{metric}_status")
        if not reuse_complete_metrics or not same_window or status not in {"COMPLETE", "ZERO_CONFIRMED"}:
            return False
        if status == "ZERO_CONFIRMED":
            return True
        return raw_path.exists() and raw_path.stat().st_size > 0

    commits_path = CANONICAL_RAW / "commits.csv"
    issues_path = CANONICAL_RAW / "issues.csv"
    prs_path = CANONICAL_RAW / "pull_requests.csv"

    if reusable("commits", commits_path):
        commits, commits_status, commits_error = [], str(prev["commits_status"]), prev.get("commits_error")
        commits_observed_rows = int(prev.get("commits_observed_rows") or 0)
        print(f"[PHASE] Reuse completed commits for {full_name}: {commits_observed_rows} rows.", flush=True)
    else:
        print(f"[PHASE] Đang tải COMMITS của {full_name}...", flush=True)
        commits, commits_status, commits_error = client.collect_commits(
            str(repo.get("full_name") or full_name), settings.study_start, settings.study_end
        )
        commits_observed_rows = None
        print(f"[PHASE] COMMITS xong: status={commits_status}, observed={len(commits)}.", flush=True)

    issues_reusable = reusable("issues", issues_path)
    prs_reusable = reusable("prs", prs_path)
    if issues_reusable and prs_reusable:
        issues, issues_status, issues_error = [], str(prev["issues_status"]), prev.get("issues_error")
        prs, prs_status, prs_error = [], str(prev["prs_status"]), prev.get("prs_error")
        issues_observed_rows = int(prev.get("issues_observed_rows") or 0)
        prs_observed_rows = int(prev.get("prs_observed_rows") or 0)
        print(
            f"[PHASE] Reuse completed Issues/PRs for {full_name}: "
            f"{issues_observed_rows} issues, {prs_observed_rows} PRs.",
            flush=True,
        )
    else:
        # One repository Issues endpoint returns both regular Issues and PR-shaped items,
        # saving many separate Search API requests for busy repositories.
        issues, prs, issues_status, prs_status, issues_error, prs_error = client.collect_issues_and_prs(
            str(repo.get("full_name") or full_name), settings.study_start, settings.study_end
        )
        issues_observed_rows = None
        prs_observed_rows = None

    commit_rows = [normalize_commit(repository_id, full_name, item, collected_at) for item in commits]
    issue_rows = [normalize_issue(repository_id, full_name, item, collected_at) for item in issues]
    pr_rows = [normalize_pr(repository_id, full_name, item, collected_at) for item in prs]
    checkpoint = {
        "repository_id": repository_id,
        "full_name": full_name,
        "sample_source": source,
        "metadata_status": "COMPLETE",
        "owner_profile_status": "COMPLETE" if profile else "ERROR",
        "commits_status": commits_status,
        "issues_status": issues_status,
        "prs_status": prs_status,
        "commits_observed_rows": len(commit_rows) if commits_observed_rows is None else commits_observed_rows,
        "issues_observed_rows": len(issue_rows) if issues_observed_rows is None else issues_observed_rows,
        "prs_observed_rows": len(pr_rows) if prs_observed_rows is None else prs_observed_rows,
        "commits_error": commits_error,
        "issues_error": issues_error,
        "prs_error": prs_error,
        "collected_at": collected_at,
        "study_start": settings.study_start,
        "study_end": settings.study_end,
    }
    owner_record = None
    if profile:
        owner_record = {
            "owner_login": owner_login,
            "owner_type": owner_type or profile.get("type"),
            "owner_id": profile.get("id"),
            "owner_profile_location": raw_location,
            "owner_country": owner_country,
            "owner_country_status": "RECOGNIZED" if owner_country else "UNKNOWN",
            "public_repos": profile.get("public_repos"),
            "followers": profile.get("followers"),
            "created_at": profile.get("created_at"),
            "html_url": profile.get("html_url"),
            "collected_at": collected_at,
        }
    return meta, owner_record, checkpoint, commit_rows, issue_rows, pr_rows


def deduplicate_raw_files() -> list[dict[str, Any]]:
    specs = [
        (CANONICAL_RAW / "commits.csv", "commit_sha"),
        (CANONICAL_RAW / "issues.csv", "issue_id"),
        (CANONICAL_RAW / "pull_requests.csv", "pr_id"),
        (CANONICAL_RAW / "owner_profiles.csv", "owner_login"),
    ]
    audit: list[dict[str, Any]] = []
    for path, key in specs:
        frame = read_csv_if_exists(path)
        if frame.empty or key not in frame.columns:
            audit.append({"table_name": path.stem, "key": key, "rows_before": 0, "rows_after": 0, "duplicates_removed": 0})
            continue
        before = len(frame)
        frame = frame.dropna(subset=[key]).drop_duplicates(subset=[key], keep="last")
        after = len(frame)
        write_frame(path, frame)
        audit.append({
            "table_name": path.stem,
            "key": key,
            "rows_before": before,
            "rows_after": after,
            "duplicates_removed": before - after,
        })
    write_frame(CANONICAL_PROCESSED / "deduplication_audit.csv", pd.DataFrame(audit))
    return audit


def _valid_count(status: Any, count: int | None) -> float:
    if status == "ZERO_CONFIRMED":
        return 0
    if status == "COMPLETE" and count is not None:
        return int(count)
    return float("nan")


def build_processed(settings: Settings, dedup_audit: list[dict[str, Any]] | None = None) -> None:
    CANONICAL_PROCESSED.mkdir(parents=True, exist_ok=True)
    repos = read_csv_if_exists(CANONICAL_RAW / "repositories.csv")
    checkpoints = read_csv_if_exists(CHECKPOINT_PATH)
    if repos.empty:
        raise RuntimeError("Chưa có metadata repository để tổng hợp.")
    if not checkpoints.empty:
        repos = repos.sort_values("snapshot_at" if "snapshot_at" in repos.columns else "collected_at").drop_duplicates(
            subset=["repository_id"], keep="last"
        )
        checkpoints = checkpoints.sort_values("collected_at").drop_duplicates(subset=["full_name"], keep="last")
    else:
        checkpoints = pd.DataFrame(columns=["full_name", "commits_status", "issues_status", "prs_status"])

    error_status_columns = ["metadata_status", "owner_profile_status", "commits_status", "issues_status", "prs_status"]
    detail_columns = [
        "repository_id", "full_name", "sample_source", "metadata_status", "owner_profile_status",
        "commits_status", "issues_status", "prs_status", "commits_error", "issues_error",
        "prs_error", "error", "commits_observed_rows", "issues_observed_rows",
        "prs_observed_rows", "study_start", "study_end", "collected_at",
    ]
    if not checkpoints.empty:
        trouble_mask = pd.Series(False, index=checkpoints.index)
        for status_col in error_status_columns:
            if status_col in checkpoints.columns:
                valid_statuses = {"COMPLETE", "ZERO_CONFIRMED"}
                if status_col == "owner_profile_status":
                    valid_statuses = {"COMPLETE"}
                trouble_mask = trouble_mask | ~checkpoints[status_col].isin(valid_statuses)
        error_details = checkpoints.loc[trouble_mask, [col for col in detail_columns if col in checkpoints.columns]].copy()
    else:
        error_details = pd.DataFrame(columns=detail_columns)
    write_frame(CANONICAL_PROCESSED / "collection_errors.csv", error_details)

    commits = read_csv_if_exists(CANONICAL_RAW / "commits.csv")
    issues = read_csv_if_exists(CANONICAL_RAW / "issues.csv")
    prs = read_csv_if_exists(CANONICAL_RAW / "pull_requests.csv")
    commit_counts = commits.groupby("repository_id")["commit_sha"].nunique().to_dict() if not commits.empty else {}
    issue_counts = issues.groupby("repository_id")["issue_id"].nunique().to_dict() if not issues.empty else {}
    pr_counts = prs.groupby("repository_id")["pr_id"].nunique().to_dict() if not prs.empty else {}
    checkpoint_by_name = checkpoints.set_index("full_name").to_dict("index") if not checkpoints.empty else {}

    result: list[dict[str, Any]] = []
    for record in repos.to_dict("records"):
        repo_id = record.get("repository_id")
        full_name = str(record.get("full_name"))
        statuses = checkpoint_by_name.get(full_name, {})
        commit_status = statuses.get("commits_status", "NOT_RUN")
        issue_status = statuses.get("issues_status", "NOT_RUN")
        pr_status = statuses.get("prs_status", "NOT_RUN")
        commit_n = int(commit_counts.get(repo_id, 0))
        issue_n = int(issue_counts.get(repo_id, 0))
        pr_n = int(pr_counts.get(repo_id, 0))
        result.append({
            **record,
            "commits_count_window": _valid_count(commit_status, commit_n),
            "issues_created_count_window": _valid_count(issue_status, issue_n),
            "prs_created_count_window": _valid_count(pr_status, pr_n),
            "commits_status": commit_status,
            "issues_status": issue_status,
            "prs_status": pr_status,
            "study_start": settings.study_start,
            "study_end": settings.study_end,
        })
    metrics = pd.DataFrame(result)
    if "repository_id" not in metrics:
        raise RuntimeError("Thiếu repository_id trong metadata; cần làm mới collection.")
    metrics = metrics.drop_duplicates(subset=["repository_id"], keep="last")
    write_frame(CANONICAL_PROCESSED / "repository_country_metrics.csv", metrics)

    def aggregate_country(frame: pd.DataFrame, key: str) -> list[dict[str, Any]]:
        summaries = []
        for country, group in frame.groupby(key, dropna=False):
            sums: dict[str, Any] = {
                "owner_country": country if pd.notna(country) and str(country).strip() else "Unknown / unresolved",
                "repositories_total": int(group["repository_id"].nunique()),
                "repositories_with_complete_commits": int(group["commits_status"].isin(["COMPLETE", "ZERO_CONFIRMED"]).sum()),
                "repositories_with_complete_issues": int(group["issues_status"].isin(["COMPLETE", "ZERO_CONFIRMED"]).sum()),
                "repositories_with_complete_prs": int(group["prs_status"].isin(["COMPLETE", "ZERO_CONFIRMED"]).sum()),
                "stars_sum_snapshot": pd.to_numeric(group["stars_snapshot"], errors="coerce").sum(min_count=1),
                "stars_avg_snapshot": pd.to_numeric(group["stars_snapshot"], errors="coerce").mean(),
                "forks_sum_snapshot": pd.to_numeric(group["forks_snapshot"], errors="coerce").sum(min_count=1),
                "forks_avg_snapshot": pd.to_numeric(group["forks_snapshot"], errors="coerce").mean(),
            }
            for metric, status_col, output_prefix in [
                ("commits_count_window", "commits_status", "commits"),
                ("issues_created_count_window", "issues_status", "issues"),
                ("prs_created_count_window", "prs_status", "prs"),
            ]:
                valid = group[group[status_col].isin(["COMPLETE", "ZERO_CONFIRMED"])]
                values = pd.to_numeric(valid[metric], errors="coerce")
                sums[f"{output_prefix}_sum_complete"] = values.sum(min_count=1)
                sums[f"{output_prefix}_avg_per_repo_complete"] = values.mean()
            summaries.append(sums)
        return summaries

    metrics["country_group_key"] = metrics["owner_country"].fillna("Unknown / unresolved")
    country_rows = aggregate_country(metrics, "country_group_key")
    write_frame(CANONICAL_PROCESSED / "country_repository_comparison.csv", pd.DataFrame(country_rows))

    def build_group(label: str, group: pd.DataFrame) -> dict[str, Any]:
        row = {
            "comparison_group": label,
            "repositories_total": int(group["repository_id"].nunique()),
            "repositories_with_complete_commits": int(group["commits_status"].isin(["COMPLETE", "ZERO_CONFIRMED"]).sum()),
            "repositories_with_complete_issues": int(group["issues_status"].isin(["COMPLETE", "ZERO_CONFIRMED"]).sum()),
            "repositories_with_complete_prs": int(group["prs_status"].isin(["COMPLETE", "ZERO_CONFIRMED"]).sum()),
        }
        for col in ["stars_snapshot", "forks_snapshot"]:
            prefix = "stars" if col == "stars_snapshot" else "forks"
            values = pd.to_numeric(group[col], errors="coerce")
            row[f"{prefix}_sum_snapshot"] = values.sum(min_count=1)
            row[f"{prefix}_avg_snapshot"] = values.mean()
        for metric, status_col, prefix in [
            ("commits_count_window", "commits_status", "commits"),
            ("issues_created_count_window", "issues_status", "issues"),
            ("prs_created_count_window", "prs_status", "prs"),
        ]:
            values = pd.to_numeric(group.loc[group[status_col].isin(["COMPLETE", "ZERO_CONFIRMED"]), metric], errors="coerce")
            row[f"{prefix}_sum_complete"] = values.sum(min_count=1)
            row[f"{prefix}_avg_per_repo_complete"] = values.mean()
        return row

    known = metrics[metrics["owner_country"].notna()]
    vietnam = metrics[metrics["owner_country"].eq("Vietnam")]
    other = known[~known["owner_country"].eq("Vietnam")]
    unknown = metrics[metrics["owner_country"].isna()]
    fixed_groups = [
        build_group("Vietnam", vietnam),
        build_group("Other recognized countries", other),
        build_group("Unknown / unresolved", unknown),
    ]
    write_frame(CANONICAL_PROCESSED / "vietnam_vs_other_countries_comparison.csv", pd.DataFrame(fixed_groups))

    # Monthly trend includes only repositories with complete collection status for each metric.
    # Missing activity in a complete repository-month is a confirmed zero; incomplete repositories are excluded.
    months = [str(period) for period in pd.period_range(
        start=pd.Period(settings.study_start[:7], freq="M"),
        end=pd.Period(settings.study_end[:7], freq="M"), freq="M"
    )]
    monthly_rows: list[dict[str, Any]] = []
    countries = sorted(metrics["owner_country"].fillna("Unknown / unresolved").astype(str).unique().tolist())
    metric_specs = [
        ("commits", commits, "committer_date", "commits_status", "commit_sha"),
        ("issues", issues, "created_at", "issues_status", "issue_id"),
        ("prs", prs, "created_at", "prs_status", "pr_id"),
    ]
    monthly_values: dict[str, dict[tuple[str, str], int]] = {}
    coverage_values: dict[str, dict[str, int]] = {}
    for metric_name, event_frame, date_col, status_col, id_col in metric_specs:
        valid_repos = metrics[metrics[status_col].isin(["COMPLETE", "ZERO_CONFIRMED"])]
        valid_ids = set(valid_repos["repository_id"].astype(str))
        coverage_values[metric_name] = {
            str(country): int(group["repository_id"].nunique())
            for country, group in valid_repos.assign(
                owner_country=valid_repos["owner_country"].fillna("Unknown / unresolved")
            ).groupby("owner_country")
        }
        if event_frame.empty or date_col not in event_frame.columns:
            monthly_values[metric_name] = {}
            continue
        events = event_frame[event_frame["repository_id"].astype(str).isin(valid_ids)].copy()
        events["_date"] = pd.to_datetime(events[date_col], errors="coerce", utc=True)
        events = events[events["_date"].notna()].copy()
        events["activity_month"] = events["_date"].dt.tz_localize(None).dt.to_period("M").astype(str)
        country_lookup = metrics[["repository_id", "owner_country"]].copy()
        country_lookup["repository_id"] = country_lookup["repository_id"].astype(str)
        country_lookup["owner_country"] = country_lookup["owner_country"].fillna("Unknown / unresolved")
        events["repository_id"] = events["repository_id"].astype(str)
        events = events.merge(country_lookup, on="repository_id", how="left", suffixes=("", "_dim"))
        country_col = "owner_country_dim" if "owner_country_dim" in events.columns else "owner_country"
        events[country_col] = events[country_col].fillna("Unknown / unresolved")
        aggregated = events.groupby(["activity_month", country_col])[id_col].nunique()
        monthly_values[metric_name] = {(str(month), str(country)): int(value) for (month, country), value in aggregated.items()}

    for month in months:
        for country in countries:
            row: dict[str, Any] = {"activity_month": month, "owner_country": country}
            for metric_name, _, _, _, _ in metric_specs:
                row[f"{metric_name}_count_complete"] = monthly_values[metric_name].get((month, country), 0)
                row[f"{metric_name}_repositories_covered"] = coverage_values[metric_name].get(country, 0)
            monthly_rows.append(row)
    write_frame(CANONICAL_PROCESSED / "monthly_activity.csv", pd.DataFrame(monthly_rows))

    # Contributor ranking is based only on repositories whose corresponding metric was completely collected.
    developer_counts: dict[str, dict[str, int]] = {}
    actor_specs = [
        ("commits", commits, "commits_status", "author_login", "commit_sha"),
        ("issues_created", issues, "issues_status", "creator_login", "issue_id"),
        ("prs_created", prs, "prs_status", "creator_login", "pr_id"),
    ]
    for metric_name, event_frame, status_col, actor_col, id_col in actor_specs:
        if event_frame.empty or actor_col not in event_frame.columns or id_col not in event_frame.columns:
            continue
        valid_ids = set(metrics.loc[metrics[status_col].isin(["COMPLETE", "ZERO_CONFIRMED"]), "repository_id"].astype(str))
        events = event_frame[event_frame["repository_id"].astype(str).isin(valid_ids)].dropna(subset=[actor_col, id_col])
        if events.empty:
            continue
        counts = events.groupby(actor_col)[id_col].nunique()
        for login, count in counts.items():
            developer_counts.setdefault(str(login), {})[metric_name] = int(count)
    developer_rows = []
    for login, values in developer_counts.items():
        commits_count = values.get("commits", 0)
        issues_count = values.get("issues_created", 0)
        prs_count = values.get("prs_created", 0)
        developer_rows.append({
            "developer_login": login,
            "commits_count_complete": commits_count,
            "issues_created_count_complete": issues_count,
            "prs_created_count_complete": prs_count,
            "total_contributions_observed_complete": commits_count + issues_count + prs_count,
        })
    developers_summary = pd.DataFrame(developer_rows)
    if not developers_summary.empty:
        developers_summary = developers_summary.sort_values(
            "total_contributions_observed_complete", ascending=False
        )
    write_frame(CANONICAL_PROCESSED / "developer_activity_summary.csv", developers_summary)

    quality: list[dict[str, Any]] = []
    def add_check(table: str, check: str, value: Any, status: str, details: str = "") -> None:
        quality.append({
            "table_name": table, "check_name": check, "observed_value": value,
            "status": status, "details": details, "checked_at": utc_now(),
        })
    add_check("repository_country_metrics", "row_count", len(metrics), "INFO")
    add_check("repository_country_metrics", "unique_repository_id", int(metrics["repository_id"].nunique()),
              "PASS" if metrics["repository_id"].is_unique else "FAIL")
    add_check("repository_country_metrics", "owner_country_recognized",
              int(metrics["owner_country"].notna().sum()), "INFO", "Location công khai tự khai báo, chưa xác minh độc lập.")
    for status_col in ["commits_status", "issues_status", "prs_status"]:
        counts = metrics[status_col].fillna("NOT_RUN").value_counts().to_dict()
        for status, count in counts.items():
            add_check("repository_country_metrics", f"{status_col}_{status}", int(count), "INFO")
    add_check("commits", "unique_commit_sha", int(commits["commit_sha"].nunique()) if not commits.empty else 0,
              "PASS" if commits.empty or commits["commit_sha"].is_unique else "FAIL")
    add_check("issues", "unique_issue_id", int(issues["issue_id"].nunique()) if not issues.empty else 0,
              "PASS" if issues.empty or issues["issue_id"].is_unique else "FAIL")
    add_check("pull_requests", "unique_pr_id", int(prs["pr_id"].nunique()) if not prs.empty else 0,
              "PASS" if prs.empty or prs["pr_id"].is_unique else "FAIL")
    for audit_row in (dedup_audit or []):
        add_check(
            str(audit_row["table_name"]),
            "duplicates_removed",
            int(audit_row["duplicates_removed"]),
            "INFO",
            f"key={audit_row['key']}; rows_before={audit_row['rows_before']}; rows_after={audit_row['rows_after']}",
        )
    write_frame(CANONICAL_PROCESSED / "data_quality_report.csv", pd.DataFrame(quality))


def run(args: argparse.Namespace) -> None:
    load_dotenv()
    settings = Settings.from_env()
    seed_path = Path(args.seed).resolve() if args.seed else SEED_PATH
    seed = read_seed(seed_path, args.limit_repos)
    client = GitHubClient(
        token=settings.token,
        api_base=settings.api_base,
        api_version=settings.api_version,
        timeout_seconds=settings.timeout_seconds,
        max_retries=settings.max_retries,
        requests_per_minute=settings.requests_per_minute,
    )

    if args.discover_global:
        excluded_names = set(seed["full_name"].astype(str).str.lower())
        excluded_owners = set(seed["full_name"].astype(str).str.split("/").str[0].str.lower())
        global_rows = discover_global_repositories(
            client,
            args.global_repo_limit,
            args.global_per_country,
            args.global_min_stars,
            args.global_max_stars,
            excluded_full_names=excluded_names,
            excluded_owners=excluded_owners,
        )
        if global_rows:
            global_frame = pd.DataFrame(global_rows)
            seed = pd.concat([seed, global_frame], ignore_index=True, sort=False)
            seed = seed.drop_duplicates(subset=["full_name"], keep="first").reset_index(drop=True)
            print(f"[INFO] Added {len(global_rows)} recognized international-owner repositories.")

    if args.discover_vietnam:
        print("[INFO] Discovering public GitHub owners whose profile location resolves to Vietnam...")
        extra_rows = discover_vietnam_repositories(client, args.vn_owner_limit, args.vn_repos_per_owner)
        if extra_rows:
            extra = pd.DataFrame(extra_rows)
            extra["sample_source"] = "vietnam_owner_discovery"
            seed = pd.concat([seed, extra], ignore_index=True, sort=False)
            seed = seed.drop_duplicates(subset=["full_name"], keep="first").reset_index(drop=True)
            print(f"[INFO] Added {len(extra_rows)} unique Vietnam-owner repository candidates.")
        else:
            print("[WARN] No additional Vietnam-owner repositories found. Do not interpret an empty Vietnam group as zero activity.")

    CANONICAL_RAW.mkdir(parents=True, exist_ok=True)
    checkpoint = read_csv_if_exists(CHECKPOINT_PATH)
    if not args.force_recrawl and not checkpoint.empty:
        checkpoint = checkpoint.sort_values("collected_at").drop_duplicates(subset=["full_name"], keep="last")
        checkpoint_lookup = checkpoint.set_index("full_name").to_dict("index")
    else:
        checkpoint_lookup = {}

    meta_path = CANONICAL_RAW / "repositories.csv"
    owner_path = CANONICAL_RAW / "owner_profiles.csv"
    commits_path = CANONICAL_RAW / "commits.csv"
    issues_path = CANONICAL_RAW / "issues.csv"
    prs_path = CANONICAL_RAW / "pull_requests.csv"

    total = len(seed)
    for index, seed_row in enumerate(seed.to_dict("records"), start=1):
        full_name = str(seed_row["full_name"])
        existing = checkpoint_lookup.get(full_name)
        same_window = bool(
            existing
            and str(existing.get("study_start")) == settings.study_start
            and str(existing.get("study_end")) == settings.study_end
        )
        if existing and not args.force_recrawl:
            metrics_complete = all(
                existing.get(k) in {"COMPLETE", "ZERO_CONFIRMED"}
                for k in ["commits_status", "issues_status", "prs_status"]
            )
            if same_window and existing.get("metadata_status") == "COMPLETE" and metrics_complete:
                print(f"[{index}/{total}] SKIP complete checkpoint: {full_name}")
                continue

        print(f"[{index}/{total}] Crawling {full_name}")
        reusable_checkpoint = existing if same_window and not args.force_recrawl else None
        meta, owner, checkpoint_row, commit_rows, issue_rows, pr_rows = collect_one(
            client,
            seed_row,
            settings,
            previous_checkpoint=reusable_checkpoint,
            reuse_complete_metrics=not args.force_recrawl,
        )
        # Append event rows first, then write checkpoint. If interrupted between steps,
        # the final deduplication is keyed by GitHub IDs and is safe to repeat.
        # Keep failed repository placeholders when the seed provides a stable ID,
        # so the quality report can distinguish failed collection from absent sample rows.
        if meta.get("repository_id") is not None:
            upsert_by_key(meta_path, [meta], "repository_id")
        if owner:
            write_append(owner_path, [owner])
        write_append(commits_path, commit_rows)
        write_append(issues_path, issue_rows)
        write_append(prs_path, pr_rows)
        upsert_by_key(CHECKPOINT_PATH, [checkpoint_row], "full_name")
        print(
            f"  metadata={checkpoint_row.get('metadata_status', 'UNKNOWN')}, "
            f"commit={checkpoint_row.get('commits_status')} ({len(commit_rows)} newly observed), "
            f"issue={checkpoint_row.get('issues_status')} ({len(issue_rows)} newly observed), "
            f"pr={checkpoint_row.get('prs_status')} ({len(pr_rows)} newly observed)"
        )
        if checkpoint_row.get("metadata_status") == "ERROR":
            print(f"  [ERROR] Repository metadata failed: {checkpoint_row.get('error') or meta.get('metadata_error')}")
        for metric in ["commits", "issues", "prs"]:
            metric_error = checkpoint_row.get(f"{metric}_error")
            if metric_error:
                print(f"  [WARN] {metric} collection issue: {metric_error}")

    # Fail with an actionable message if no repository metadata was collected.
    # This is especially important for a one-repository smoke test with a bad token or a removed repo.
    collected_metadata = read_csv_if_exists(meta_path)
    if collected_metadata.empty or "repository_id" not in collected_metadata.columns:
        failed_checkpoints = read_csv_if_exists(CHECKPOINT_PATH)
        errors = []
        if not failed_checkpoints.empty and "error" in failed_checkpoints.columns:
            errors = [
                f"{row.get('full_name')}: {row.get('error')}"
                for row in failed_checkpoints.to_dict("records")
                if row.get("metadata_status") == "ERROR" and row.get("error")
            ]
        print("\n[STOP] GitHub chưa trả về metadata cho repository nào; chưa tạo processed CSV.")
        if errors:
            print("[DIAGNOSTIC] Nguyên nhân API:")
            for error in errors[-5:]:
                print(f"  - {error}")
        print("Kiểm tra token trong .env, sau đó chạy lại. Không cần xóa raw data hoặc checkpoint.")
        return
    if not collected_metadata.get("metadata_status", pd.Series(dtype=str)).eq("COMPLETE").any():
        print("\n[STOP] Không có repository nào thu thập metadata thành công; chưa tạo processed CSV.")
        print("Kiểm tra thông báo [ERROR] phía trên. Không cần xóa raw data hoặc checkpoint.")
        return

    dedup_audit = deduplicate_raw_files()
    build_processed(settings, dedup_audit)
    print(f"[DONE] Canonical raw: {CANONICAL_RAW}")
    print(f"[DONE] Canonical processed: {CANONICAL_PROCESSED}")
    print("[NOTE] Counts are blank for PARTIAL/ERROR/NOT_RUN metrics; observed partial rows remain only in raw files.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Canonical GitHub Developer Analytics pipeline")
    parser.add_argument("--seed", help="CSV path listing seed repositories; defaults to data/raw/repositories_stage2.csv")
    parser.add_argument("--limit-repos", type=int, help="Test with the first N repositories")
    parser.add_argument("--force-recrawl", action="store_true", help="Recollect all metrics and refresh Stars/Forks snapshot")
    parser.add_argument("--discover-vietnam", action="store_true", help="Add repositories from public owner profiles located in Vietnam")
    parser.add_argument("--vn-owner-limit", type=int, default=30)
    parser.add_argument("--vn-repos-per-owner", type=int, default=10)
    parser.add_argument("--discover-global", action="store_true", help="Add repositories whose owners have recognized non-Vietnam public locations")
    parser.add_argument("--global-repo-limit", type=int, default=12, help="Maximum recognized international-owner repositories to add")
    parser.add_argument("--global-per-country", type=int, default=3, help="Maximum discovered repositories per non-Vietnam owner country")
    parser.add_argument("--global-min-stars", type=int, default=50)
    parser.add_argument("--global-max-stars", type=int, default=5000)
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
