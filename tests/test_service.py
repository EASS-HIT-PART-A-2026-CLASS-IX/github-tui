import asyncio

from github_insights.core.service import GitHubInsightsService


class StubDataClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def fetch_user(self, username: str) -> dict[str, object]:
        self.calls.append(("user", username))
        return {"login": username, "followers": 3, "following": 1, "public_repos": 2}

    async def fetch_repos(self, username: str) -> list[dict[str, object]]:
        self.calls.append(("repos", username))
        return [
            {"name": "one", "stargazers_count": 4, "forks_count": 1, "language": "Python"},
            {"name": "two", "stargazers_count": 2, "forks_count": 0, "language": "Go"},
        ]


def test_service_load_snapshot_trims_username_and_computes_metrics() -> None:
    client = StubDataClient()
    service = GitHubInsightsService(client)

    snapshot = asyncio.run(service.load_snapshot("  octocat  "))

    assert snapshot.user["login"] == "octocat"
    assert snapshot.metrics.total_stars == 6
    assert snapshot.metrics.total_forks == 1
    assert snapshot.metrics.score == 27
    assert client.calls == [("user", "octocat"), ("repos", "octocat")]


def test_service_load_snapshot_rejects_empty_username() -> None:
    client = StubDataClient()
    service = GitHubInsightsService(client)

    try:
        asyncio.run(service.load_snapshot("   "))
    except ValueError as exc:
        assert str(exc) == "GitHub username is required."
    else:
        raise AssertionError("Expected ValueError for blank username.")
