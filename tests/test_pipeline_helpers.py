from github_analytics.country import resolve_country
from github_analytics.pipeline import _valid_count, normalize_issue, normalize_pr, normalize_commit


def test_resolves_explicit_vietnam_locations():
    assert resolve_country("Hanoi, Vietnam") == "Vietnam"
    assert resolve_country("Ho Chi Minh City") == "Vietnam"
    assert resolve_country("Viet Nam") == "Vietnam"


def test_unknown_locations_are_not_guessed():
    assert resolve_country(None) is None
    assert resolve_country("") is None
    assert resolve_country("Somewhere") is None
    assert resolve_country("CA") is None


def test_valid_count_respects_collection_status():
    assert _valid_count("COMPLETE", 12) == 12
    assert _valid_count("ZERO_CONFIRMED", 0) == 0
    assert _valid_count("PARTIAL", 12) != _valid_count("COMPLETE", 12)
    assert _valid_count("ERROR", 0) != 0
    assert _valid_count("NOT_RUN", 0) != 0


def test_commit_normalization_preserves_github_ids_and_dates():
    row = normalize_commit(123, "a/b", {
        "sha": "abc123", "html_url": "https://github.com/a/b/commit/abc123",
        "author": {"login": "dev"},
        "commit": {"message": "fix", "author": {"name": "Dev", "date": "2025-01-01T10:00:00Z"},
                   "committer": {"date": "2025-01-01T10:01:00Z"}},
    }, "2026-10-25T00:00:00+00:00")
    assert row["repository_id"] == 123
    assert row["commit_sha"] == "abc123"
    assert row["author_login"] == "dev"
    assert row["author_date"].startswith("2025-01-01")


def test_issue_and_pr_normalization_use_different_keys():
    issue = normalize_issue(123, "a/b", {"id": 1, "number": 2, "created_at": "2025-01-01"}, "now")
    pr = normalize_pr(123, "a/b", {"id": 2, "number": 3, "created_at": "2025-01-01"}, "now")
    assert issue["issue_id"] == 1
    assert pr["pr_id"] == 2

def test_request_throttle_waits_once_then_clears_expired_slots(monkeypatch):
    import github_analytics.github_api as api_module
    from github_analytics.github_api import GitHubClient

    clock = [0.0]

    def fake_monotonic():
        return clock[0]

    def fake_sleep(seconds):
        clock[0] += seconds

    monkeypatch.setattr(api_module.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(api_module.time, "sleep", fake_sleep)
    client = GitHubClient(token="test-token", requests_per_minute=2)

    client._throttle()
    client._throttle()
    assert len(client._request_times) == 2

    client._throttle()
    assert clock[0] >= 60
    assert len(client._request_times) == 1

    client._throttle()
    assert len(client._request_times) == 2
    assert clock[0] < 61

def test_processed_build_creates_repository_monthly_and_developer_outputs(tmp_path, monkeypatch):
    import pandas as pd
    import github_analytics.pipeline as pipeline
    from github_analytics.config import Settings

    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    raw.mkdir()
    processed.mkdir()
    monkeypatch.setattr(pipeline, "CANONICAL_RAW", raw)
    monkeypatch.setattr(pipeline, "CANONICAL_PROCESSED", processed)
    monkeypatch.setattr(pipeline, "CHECKPOINT_PATH", raw / "repository_checkpoint.csv")

    pd.DataFrame([{
        "repository_id": 1, "full_name": "org/repo", "owner_country": "Vietnam",
        "owner_country_status": "RECOGNIZED", "owner_login": "org", "language": "Python",
        "stars_snapshot": 10, "forks_snapshot": 2, "sample_source": "global_seed",
        "snapshot_at": "2026-10-25T00:00:00+00:00", "metadata_status": "COMPLETE",
    }]).to_csv(raw / "repositories.csv", index=False)
    pd.DataFrame([{
        "repository_id": 1, "full_name": "org/repo",
        "commits_status": "COMPLETE", "issues_status": "ZERO_CONFIRMED",
        "prs_status": "COMPLETE", "collected_at": "2026-10-25T00:00:00+00:00",
        "study_start": "2020-01-01", "study_end": "2026-10-20",
    }]).to_csv(raw / "repository_checkpoint.csv", index=False)
    pd.DataFrame([{
        "repository_id": 1, "full_name": "org/repo", "commit_sha": "sha-1",
        "author_login": "dev1", "committer_date": "2020-01-03T10:00:00Z",
    }]).to_csv(raw / "commits.csv", index=False)
    pd.DataFrame(columns=["repository_id", "full_name", "issue_id", "created_at", "creator_login"]).to_csv(
        raw / "issues.csv", index=False
    )
    pd.DataFrame([{
        "repository_id": 1, "full_name": "org/repo", "pr_id": 22,
        "created_at": "2020-02-05T10:00:00Z", "creator_login": "dev1",
    }]).to_csv(raw / "pull_requests.csv", index=False)

    settings = Settings(token="dummy", study_start="2020-01-01", study_end="2026-10-20")
    pipeline.build_processed(settings)

    metrics = pd.read_csv(processed / "repository_country_metrics.csv")
    assert len(metrics) == 1
    assert metrics.loc[0, "commits_count_window"] == 1
    assert metrics.loc[0, "issues_created_count_window"] == 0
    assert metrics.loc[0, "prs_created_count_window"] == 1

    monthly = pd.read_csv(processed / "monthly_activity.csv")
    january = monthly[monthly["activity_month"] == "2020-01"].iloc[0]
    february = monthly[monthly["activity_month"] == "2020-02"].iloc[0]
    assert january["commits_count_complete"] == 1
    assert january["issues_count_complete"] == 0
    assert february["prs_count_complete"] == 1

    developers = pd.read_csv(processed / "developer_activity_summary.csv")
    dev = developers[developers["developer_login"] == "dev1"].iloc[0]
    assert dev["commits_count_complete"] == 1
    assert dev["prs_created_count_complete"] == 1

    assert (processed / "country_repository_comparison.csv").exists()
    assert (processed / "vietnam_vs_other_countries_comparison.csv").exists()
    assert (processed / "data_quality_report.csv").exists()
