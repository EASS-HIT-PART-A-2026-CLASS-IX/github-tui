from __future__ import annotations

from typing import Any, Protocol

from .metrics import summarize_metrics
from .models import AIInsights, InsightsSnapshot, RepoMetrics


class GitHubDataClient(Protocol):
    async def fetch_user(self, username: str) -> dict[str, Any]:
        ...

    async def fetch_repos(self, username: str) -> list[dict[str, Any]]:
        ...


class DeepInsightsGenerator(Protocol):
    async def generate(
        self,
        *,
        username: str,
        user: dict[str, Any],
        repos: list[dict[str, Any]],
        metrics: RepoMetrics,
    ) -> AIInsights:
        ...


class GitHubInsightsService:
    def __init__(
        self,
        data_client: GitHubDataClient,
        *,
        deep_insights_generator: DeepInsightsGenerator | None = None,
    ) -> None:
        self._data_client = data_client
        self._deep_insights_generator = deep_insights_generator

    async def load_snapshot(
        self,
        username: str,
        *,
        include_llm: bool = False,
    ) -> InsightsSnapshot:
        cleaned = username.strip()
        if not cleaned:
            raise ValueError("GitHub username is required.")

        user = await self._data_client.fetch_user(cleaned)
        repos = await self._data_client.fetch_repos(cleaned)
        metrics = summarize_metrics(user, repos)
        snapshot = InsightsSnapshot(user=user, repos=repos, metrics=metrics)

        if include_llm and self._deep_insights_generator is not None:
            snapshot.ai_insights = await self._deep_insights_generator.generate(
                username=cleaned,
                user=user,
                repos=repos,
                metrics=metrics,
            )

        return snapshot
