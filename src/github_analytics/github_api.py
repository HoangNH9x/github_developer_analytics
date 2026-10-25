"""Small, retry-aware GitHub REST API client for the project."""
from __future__ import annotations

import time
from collections import deque
from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests


class GitHubAPIError(RuntimeError):
    pass


class GitHubClient:
    def __init__(
        self,
        token: str,
        api_base: str = "https://api.github.com",
        api_version: str = "2022-11-28",
        timeout_seconds: int = 30,
        max_retries: int = 5,
        requests_per_minute: int = 25,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.requests_per_minute = max(1, min(requests_per_minute, 28))
        self._request_times: deque[float] = deque()
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": api_version,
            "User-Agent": "github-developer-analytics-student-project",
        })

    def _throttle(self) -> None:
        while True:
            now = time.monotonic()
            while self._request_times and now - self._request_times[0] >= 60:
                self._request_times.popleft()
            if len(self._request_times) < self.requests_per_minute:
                self._request_times.append(now)
                return
            sleep_for = max(0.1, 60 - (now - self._request_times[0]) + 0.1)
            print(
                f"[RATE LIMIT] Đã gửi {self.requests_per_minute} request/phút; "
                f"tạm nghỉ khoảng {sleep_for:.0f}s rồi tiếp tục.",
                flush=True,
            )
            time.sleep(sleep_for)

    def request_json(self, url_or_path: str, params: dict[str, Any] | None = None) -> tuple[dict[str, Any] | list[Any], requests.Response]:
        url = url_or_path if url_or_path.startswith("http") else f"{self.api_base}/{url_or_path.lstrip('/')}"
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self._throttle()
            try:
                response = self.session.get(url, params=params, timeout=self.timeout_seconds)
                if response.status_code in (403, 429):
                    remaining = response.headers.get("X-RateLimit-Remaining")
                    retry_after = response.headers.get("Retry-After")
                    reset_at = response.headers.get("X-RateLimit-Reset")
                    if retry_after:
                        wait = max(1, int(retry_after))
                    elif remaining == "0" and reset_at:
                        wait = max(1, int(reset_at) - int(time.time()) + 1)
                    else:
                        wait = min(2 ** attempt, 60)
                    if attempt < self.max_retries:
                        print(
                            f"[GITHUB RATE LIMIT] HTTP {response.status_code}; "
                            f"thử lại sau khoảng {wait}s (lần {attempt + 1}/{self.max_retries}).",
                            flush=True,
                        )
                        time.sleep(wait)
                        continue
                if response.status_code >= 500 and attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 30))
                    continue
                if not response.ok:
                    raise GitHubAPIError(
                        f"GitHub API {response.status_code} for {response.url}: "
                        f"{response.text[:500]}"
                    )
                return response.json(), response
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(min(2 ** attempt, 30))
        raise GitHubAPIError(f"GitHub request failed after retries: {last_error}")

    def get_one(self, path: str) -> dict[str, Any]:
        payload, _ = self.request_json(path)
        if not isinstance(payload, dict):
            raise GitHubAPIError(f"Expected JSON object from {path}")
        return payload

    def get_all_pages(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        url = path if path.startswith("http") else f"{self.api_base}/{path.lstrip('/')}"
        current_params = dict(params or {})
        current_params.setdefault("per_page", 100)
        rows: list[dict[str, Any]] = []
        page_number = 0
        endpoint_label = path.split("?")[0].rstrip("/").split("/")[-1]
        while url:
            payload, response = self.request_json(url, params=current_params)
            current_params = {}  # next link already contains its query params
            if not isinstance(payload, list):
                raise GitHubAPIError(f"Expected JSON list from {response.url}")
            page_number += 1
            page_rows = [item for item in payload if isinstance(item, dict)]
            rows.extend(page_rows)
            # Print a heartbeat on every page: highly active repositories can be large,
            # and without this message a user may think the process is frozen.
            print(
                f"[PAGINATION] {endpoint_label}: trang {page_number}, "
                f"+{len(page_rows)} bản ghi; đã đọc {len(rows)}.",
                flush=True,
            )
            next_link = response.links.get("next", {}).get("url")
            url = next_link if next_link else ""
        return rows

    def owner_profile(self, owner_login: str, owner_type: str | None = None) -> dict[str, Any]:
        candidates = []
        if owner_type and owner_type.lower() == "organization":
            candidates = [f"orgs/{owner_login}", f"users/{owner_login}"]
        else:
            candidates = [f"users/{owner_login}", f"orgs/{owner_login}"]
        last_error: Exception | None = None
        for path in candidates:
            try:
                return self.get_one(path)
            except GitHubAPIError as exc:
                if "API 404" not in str(exc):
                    raise
                last_error = exc
        raise GitHubAPIError(f"Owner profile not found for {owner_login}: {last_error}")

    @staticmethod
    def _day_range(start: str, end: str) -> tuple[date, date]:
        return date.fromisoformat(start), date.fromisoformat(end)

    def search_issues_or_prs(
        self, full_name: str, kind: str, start: str, end: str
    ) -> tuple[list[dict[str, Any]], str, str | None]:
        """Collect issue or PR records. Search windows are split before hitting GitHub's 1,000-result cap."""
        if kind not in {"issue", "pr"}:
            raise ValueError("kind must be 'issue' or 'pr'")
        collected: dict[str, dict[str, Any]] = {}
        statuses: list[str] = []
        errors: list[str] = []

        def fetch_window(window_start: date, window_end: date) -> None:
            query = (
                f"repo:{full_name} is:{kind} "
                f"created:{window_start.isoformat()}..{window_end.isoformat()}"
            )
            payload, _ = self.request_json("search/issues", {"q": query, "per_page": 100, "page": 1})
            assert isinstance(payload, dict)
            total = int(payload.get("total_count", 0))
            incomplete = bool(payload.get("incomplete_results", False))
            print(
                f"[SEARCH] {kind.upper()} {full_name}: {window_start}..{window_end}, "
                f"{total} kết quả ước tính"
                + (" (incomplete_results=true)" if incomplete else ""),
                flush=True,
            )
            if (total >= 950 or incomplete) and window_start < window_end:
                midpoint = window_start + (window_end - window_start) // 2
                print(
                    f"[SEARCH] Chia khoảng ngày vì gần giới hạn kết quả: "
                    f"{window_start}..{midpoint} và {midpoint + timedelta(days=1)}..{window_end}",
                    flush=True,
                )
                fetch_window(window_start, midpoint)
                fetch_window(midpoint + timedelta(days=1), window_end)
                return
            if total >= 950 or incomplete:
                statuses.append("PARTIAL")
            # Search API will only expose up to 1,000 results for this query.
            pages = (min(total, 1000) + 99) // 100
            for page in range(1, pages + 1):
                page_payload, _ = self.request_json(
                    "search/issues", {"q": query, "per_page": 100, "page": page}
                )
                assert isinstance(page_payload, dict)
                page_items = page_payload.get("items", [])
                for item in page_items:
                    item_id = str(item.get("id") or item.get("node_id") or item.get("html_url"))
                    if item_id and item_id != "None":
                        collected[item_id] = item
                print(
                    f"[SEARCH PAGE] {kind.upper()} {full_name}: trang {page}/{pages}, "
                    f"+{len(page_items)} bản ghi; đã thu thập duy nhất {len(collected)}.",
                    flush=True,
                )
                if page_payload.get("incomplete_results"):
                    statuses.append("PARTIAL")
            if total == 0 and not incomplete:
                statuses.append("ZERO_CONFIRMED")
            elif total > 0 and not (total >= 950 or incomplete):
                statuses.append("COMPLETE")

        try:
            window_start, window_end = self._day_range(start, end)
            fetch_window(window_start, window_end)
        except Exception as exc:
            errors.append(str(exc))
            statuses.append("ERROR")

        if "ERROR" in statuses:
            status = "ERROR"
        elif "PARTIAL" in statuses:
            status = "PARTIAL"
        elif not collected:
            status = "ZERO_CONFIRMED" if statuses and all(s == "ZERO_CONFIRMED" for s in statuses) else "COMPLETE"
        else:
            status = "COMPLETE"
        return list(collected.values()), status, "; ".join(errors) or None

    def collect_commits(self, full_name: str, start: str, end: str) -> tuple[list[dict[str, Any]], str, str | None]:
        since = f"{start}T00:00:00Z"
        until = f"{end}T23:59:59Z"
        try:
            rows = self.get_all_pages(
                f"repos/{full_name}/commits",
                {"since": since, "until": until, "per_page": 100},
            )
            return rows, ("COMPLETE" if rows else "ZERO_CONFIRMED"), None
        except Exception as exc:
            message = str(exc)
            # GitHub returns HTTP 409 for an existing repository with no commits.
            if "GitHub API 409" in message and "empty" in message.lower():
                return [], "ZERO_CONFIRMED", None
            return [], "ERROR", message
