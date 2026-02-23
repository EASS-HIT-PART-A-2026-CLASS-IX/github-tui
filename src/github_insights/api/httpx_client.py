import json
from typing import Any
import httpx
from .client import GitHubClient, API_HEADERS
from .exceptions import GitHubApiError
from .utils import extract_error_message

class HttpxGitHubClient(GitHubClient):
    async def _fetch_json(self, endpoint: str) -> Any:
        try:
            async with httpx.AsyncClient(
                headers=API_HEADERS, timeout=self.timeout_seconds
            ) as client:
                response = await client.get(endpoint)
        except httpx.HTTPError as exc:
            raise GitHubApiError(f"Network error while contacting GitHub: {exc}") from exc

        if response.status_code >= 400:
            message = extract_error_message(response.status_code, response.text)
            if response.status_code == 403:
                remaining = response.headers.get("x-ratelimit-remaining")
                reset_epoch = response.headers.get("x-ratelimit-reset")
                if remaining == "0" and reset_epoch:
                    message = (
                        f"{message} Rate limit exceeded; reset epoch: {reset_epoch}."
                    )
            raise GitHubApiError(message)

        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise GitHubApiError("GitHub response was not valid JSON.") from exc
