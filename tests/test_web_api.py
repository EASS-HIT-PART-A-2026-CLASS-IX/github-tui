import asyncio

import httpx

from github_insights.api.exceptions import GitHubApiError
from github_insights.core.models import AIInsights
from github_insights.web.app import app


class StubApiClient:
    def __init__(self) -> None:
        self.usernames: list[str] = []

    async def fetch_user(self, username: str) -> dict[str, object]:
        self.usernames.append(username)
        return {
            "login": username,
            "name": "The Octocat",
            "followers": 8,
            "following": 2,
            "public_repos": 3,
            "created_at": "2020-06-10T11:20:00Z",
        }

    async def fetch_repos(self, username: str) -> list[dict[str, object]]:
        return [
            {
                "name": "delta",
                "stargazers_count": 5,
                "forks_count": 1,
                "open_issues_count": 0,
                "language": "Go",
                "updated_at": "2025-01-12T09:00:00Z",
            },
            {
                "name": "alpha",
                "stargazers_count": 18,
                "forks_count": 4,
                "open_issues_count": 2,
                "language": "Python",
                "updated_at": "2025-02-20T09:00:00Z",
            },
        ]


class ErrorApiClient:
    async def fetch_user(self, username: str) -> dict[str, object]:
        raise GitHubApiError("Not Found (HTTP 404)")

    async def fetch_repos(self, username: str) -> list[dict[str, object]]:
        raise AssertionError("fetch_repos should not be called when fetch_user fails")


class StubDeepInsightsGenerator:
    async def generate(self, *, username: str, **_) -> AIInsights:
        return AIInsights(
            status="ready",
            model="google-gla:gemini-2.5-flash",
            summary=f"@{username} has strong repo traction and above-average maintainership signals.",
            strengths=["Strong star concentration in top repositories."],
            risks=["Issue backlog exists in high-visibility repositories."],
            recommendations=["Set response-time SLA for top-star repositories."],
        )


async def _get(path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.get(path)


def test_health_endpoint() -> None:
    response = asyncio.run(_get("/api/v1/health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_insights_endpoint_returns_summary(monkeypatch) -> None:
    stub = StubApiClient()

    def fake_factory(*, use_curl: bool = False, timeout_seconds: float = 15.0, max_repo_pages: int = 5):
        assert use_curl is True
        assert timeout_seconds == 15.0
        assert max_repo_pages == 5
        return stub

    monkeypatch.setattr("github_insights.web.app.create_github_client", fake_factory)

    response = asyncio.run(_get("/api/v1/insights/octocat?transport=curl"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["login"] == "octocat"
    assert payload["metrics"]["total_stars"] == 23
    assert payload["metrics"]["score"] == 93
    assert payload["repositories"][0]["name"] == "alpha"
    assert stub.usernames == ["octocat"]


def test_insights_endpoint_maps_github_errors(monkeypatch) -> None:
    monkeypatch.setattr(
        "github_insights.web.app.create_github_client",
        lambda **_: ErrorApiClient(),
    )

    response = asyncio.run(_get("/api/v1/insights/missing-user"))

    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found (HTTP 404)"


def test_insights_endpoint_includes_ai_block_when_llm_enabled(monkeypatch) -> None:
    stub = StubApiClient()

    monkeypatch.setattr(
        "github_insights.web.app.create_github_client",
        lambda **_: stub,
    )
    original_generator = app.state.deep_insights_generator
    app.state.deep_insights_generator = StubDeepInsightsGenerator()

    try:
        response = asyncio.run(_get("/api/v1/insights/octocat?llm=true"))
    finally:
        app.state.deep_insights_generator = original_generator

    assert response.status_code == 200
    payload = response.json()
    assert payload["ai_insights"]["status"] == "ready"
    assert payload["ai_insights"]["model"] == "google-gla:gemini-2.5-flash"
    assert payload["ai_insights"]["summary"].startswith("@octocat has strong repo traction")
