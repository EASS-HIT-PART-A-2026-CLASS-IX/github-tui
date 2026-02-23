import asyncio
import json
from typing import Any
from .client import GitHubClient, API_HEADERS
from .exceptions import GitHubApiError
from .utils import split_curl_output, extract_error_message

class CurlGitHubClient(GitHubClient):
    async def _fetch_json(self, endpoint: str) -> Any:
        command = [
            "curl",
            "-sS",
            "-L",
            "-H",
            f"Accept: {API_HEADERS['Accept']}",
            "-H",
            f"User-Agent: {API_HEADERS['User-Agent']}",
            "-H",
            f"X-GitHub-Api-Version: {API_HEADERS['X-GitHub-Api-Version']}",
            "-w",
            "\n%{http_code}",
            endpoint,
        ]

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            details = stderr.decode("utf-8", errors="replace").strip()
            raise GitHubApiError(f"curl command failed: {details or 'unknown error'}")

        output = stdout.decode("utf-8", errors="replace")
        body, status_code = split_curl_output(output)
        if status_code >= 400:
            raise GitHubApiError(extract_error_message(status_code, body))

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise GitHubApiError("curl response was not valid JSON.") from exc
