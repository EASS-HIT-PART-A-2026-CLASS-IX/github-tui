from typing import Any, Literal
from dataclasses import dataclass, field


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
class AIInsights:
    status: Literal["ready", "disabled", "error"]
    model: str | None = None
    summary: str | None = None
    strengths: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    detail: str | None = None


@dataclass(slots=True)
class InsightsSnapshot:
    user: dict[str, Any]
    repos: list[dict[str, Any]]
    metrics: RepoMetrics
    ai_insights: AIInsights | None = None
