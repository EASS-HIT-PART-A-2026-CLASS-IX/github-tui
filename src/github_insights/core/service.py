from __future__ import annotations

from typing import Any, Protocol

from .metrics import summarize_metrics
from .models import InsightsSnapshot


class GitHubDataClient(Protocol):
    async def fetch_user(self, username: str) -> dict[str, Any]:
        ...

    async def fetch_repos(self, username: str) -> list[dict[str, Any]]:
        ...


class GitHubInsightsService:
    def __init__(self, data_client: GitHubDataClient) -> None:
        self._data_client = data_client

    async def load_snapshot(self, username: str) -> InsightsSnapshot:
        cleaned = username.strip()
        if not cleaned:
            raise ValueError("GitHub username is required.")

        user = await self._data_client.fetch_user(cleaned)
        repos = await self._data_client.fetch_repos(cleaned)
        metrics = summarize_metrics(user, repos)
        return InsightsSnapshot(user=user, repos=repos, metrics=metrics)
