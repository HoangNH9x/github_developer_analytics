"""Configuration for the canonical GitHub Developer Analytics pipeline."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = REPO_ROOT / "reports"

DEFAULT_STUDY_START = "2020-01-01"
DEFAULT_STUDY_END = "2026-10-20"


@dataclass(frozen=True)
class Settings:
    token: str
    study_start: str = DEFAULT_STUDY_START
    study_end: str = DEFAULT_STUDY_END
    api_base: str = "https://api.github.com"
    api_version: str = "2022-11-28"
    timeout_seconds: int = 30
    max_retries: int = 5
    requests_per_minute: int = 25

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("GITHUB_TOKEN", "").strip()
        if not token:
            raise RuntimeError(
                "Thiếu GITHUB_TOKEN. Hãy tạo file .env local từ .env.example "
                "hoặc đặt biến môi trường GITHUB_TOKEN. Không gửi token lên chat "
                "và không commit file .env."
            )
        start = os.getenv("STUDY_START", DEFAULT_STUDY_START).strip()
        end = os.getenv("STUDY_END", DEFAULT_STUDY_END).strip()
        if start > end:
            raise ValueError(f"STUDY_START ({start}) phải <= STUDY_END ({end}).")
        return cls(
            token=token,
            study_start=start,
            study_end=end,
            timeout_seconds=int(os.getenv("GITHUB_TIMEOUT_SECONDS", "30")),
            max_retries=int(os.getenv("GITHUB_MAX_RETRIES", "5")),
            requests_per_minute=int(os.getenv("GITHUB_REQUESTS_PER_MINUTE", "25")),
        )
