from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str


class UserProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    login: str
    name: str | None = None
    bio: str | None = None
    location: str | None = None
    company: str | None = None
    avatar_url: str | None = None
    html_url: str | None = None
    followers: int = 0
    following: int = 0
    public_repos: int = 0
    joined_date: str = "-"


class RepositoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    html_url: str | None = None
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    language: str = "-"
    updated_date: str = "-"


class RepoMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


class AiInsightsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "disabled", "error"]
    model: str | None = None
    summary: str | None = None
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    detail: str | None = None


class InsightsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user: UserProfile
    metrics: RepoMetricsResponse
    repositories: list[RepositoryItem]
    ai_insights: AiInsightsResponse | None = None
