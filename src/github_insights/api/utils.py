import json
from datetime import datetime
from .exceptions import GitHubApiError

def format_iso_date(value: str | None) -> str:
    if not value:
        return "-"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return "-"
    return parsed.strftime("%Y-%m-%d")

def split_curl_output(raw_output: str) -> tuple[str, int]:
    body, sep, status_line = raw_output.rpartition("\n")
    if not sep:
        raise GitHubApiError("Could not parse curl response status code.")
    status_line = status_line.strip()
    if not status_line.isdigit():
        raise GitHubApiError("curl did not return a numeric status code.")
    return body, int(status_line)

def extract_error_message(status_code: int, response_body: str) -> str:
    default_message = f"GitHub API returned HTTP {status_code}."
    try:
        payload = json.loads(response_body)
    except json.JSONDecodeError:
        return default_message

    message = payload.get("message")
    if isinstance(message, str) and message.strip():
        return f"{message} (HTTP {status_code})"
    return default_message
