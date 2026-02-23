from .client import GitHubClient
from .httpx_client import HttpxGitHubClient
from .curl_client import CurlGitHubClient

def create_github_client(
    *,
    use_curl: bool = False,
    timeout_seconds: float = 15.0,
    max_repo_pages: int = 5,
) -> GitHubClient:
    client_kwargs = {
        "timeout_seconds": timeout_seconds,
        "max_repo_pages": max_repo_pages,
    }
    if use_curl:
        return CurlGitHubClient(**client_kwargs)
    return HttpxGitHubClient(**client_kwargs)
