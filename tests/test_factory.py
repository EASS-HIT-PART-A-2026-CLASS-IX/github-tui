from github_insights.api.curl_client import CurlGitHubClient
from github_insights.api.factory import create_github_client
from github_insights.api.httpx_client import HttpxGitHubClient


def test_factory_returns_httpx_client_by_default() -> None:
    client = create_github_client()
    assert isinstance(client, HttpxGitHubClient)


def test_factory_returns_curl_client_when_requested() -> None:
    client = create_github_client(use_curl=True)
    assert isinstance(client, CurlGitHubClient)


def test_factory_applies_shared_client_configuration() -> None:
    client = create_github_client(timeout_seconds=9.0, max_repo_pages=2)
    assert client.timeout_seconds == 9.0
    assert client.max_repo_pages == 2
