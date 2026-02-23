from typing import Any
from dataclasses import dataclass


@dataclass(slots=True)
class RepoMetrics:
    scanned_repos: int
    total_stars: int
    total_forks: int
    followers: int
    following: int
    public_repos: int
    score: int
    top_language: str
    top_repo_name: str
    top_repo_stars: int


@dataclass(slots=True)
class InsightsSnapshot:
    user: dict[str, Any]
    repos: list[dict[str, Any]]
    metrics: RepoMetrics
