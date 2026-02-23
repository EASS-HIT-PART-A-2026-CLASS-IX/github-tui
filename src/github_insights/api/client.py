import abc
from typing import Any
from .exceptions import GitHubApiError

GITHUB_API_BASE = "https://api.github.com"
API_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "github-insights-tui",
    "X-GitHub-Api-Version": "2022-11-28",
}

class GitHubClient(abc.ABC):
    def __init__(self, *, timeout_seconds: float = 15.0, max_repo_pages: int = 5) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_repo_pages = max_repo_pages

    async def fetch_user(self, username: str) -> dict[str, Any]:
        endpoint = f"{GITHUB_API_BASE}/users/{username}"
        payload = await self._fetch_json(endpoint)
        if not isinstance(payload, dict):
            raise GitHubApiError("Unexpected profile payload type from GitHub.")
        return payload

    async def fetch_repos(self, username: str) -> list[dict[str, Any]]:
        repos: list[dict[str, Any]] = []
        for page in range(1, self.max_repo_pages + 1):
            endpoint = (
                f"{GITHUB_API_BASE}/users/{username}/repos"
                f"?per_page=100&page={page}&sort=updated"
            )
            payload = await self._fetch_json(endpoint)
            if not isinstance(payload, list):
                raise GitHubApiError("Unexpected repositories payload type from GitHub.")
            repos.extend(item for item in payload if isinstance(item, dict))
            if len(payload) < 100:
                break
        return repos

    @abc.abstractmethod
    async def _fetch_json(self, endpoint: str) -> Any:
        pass
