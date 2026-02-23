from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from textual.widgets import Input

from github_insights.core.metrics import summarize_metrics
from github_insights.ui.app import GitHubInsightsApp

SAMPLE_USER = {
    "login": "openai",
    "name": "OpenAI",
    "location": "San Francisco, CA",
    "company": "@openai",
    "followers": 189000,
    "following": 0,
    "public_repos": 26,
    "bio": "OpenAI APIs and SDKs.",
    "created_at": "2015-11-03T00:00:00Z",
    "html_url": "https://github.com/openai",
}

SAMPLE_REPOS = [
    {
        "name": "openai-python",
        "stargazers_count": 29100,
        "forks_count": 4200,
        "open_issues_count": 93,
        "language": "Python",
        "updated_at": "2026-02-20T13:12:00Z",
        "html_url": "https://github.com/openai/openai-python",
    },
    {
        "name": "openai-cookbook",
        "stargazers_count": 67100,
        "forks_count": 11600,
        "open_issues_count": 184,
        "language": "Jupyter Notebook",
        "updated_at": "2026-02-18T09:40:00Z",
        "html_url": "https://github.com/openai/openai-cookbook",
    },
    {
        "name": "openai-node",
        "stargazers_count": 9400,
        "forks_count": 1200,
        "open_issues_count": 51,
        "language": "TypeScript",
        "updated_at": "2026-02-19T15:00:00Z",
        "html_url": "https://github.com/openai/openai-node",
    },
    {
        "name": "whisper",
        "stargazers_count": 81100,
        "forks_count": 9600,
        "open_issues_count": 364,
        "language": "Python",
        "updated_at": "2026-02-17T07:22:00Z",
        "html_url": "https://github.com/openai/whisper",
    },
    {
        "name": "gym",
        "stargazers_count": 36700,
        "forks_count": 10500,
        "open_issues_count": 220,
        "language": "Python",
        "updated_at": "2026-02-16T11:03:00Z",
        "html_url": "https://github.com/openai/gym",
    },
]


async def generate() -> None:
    output_dir = PROJECT_ROOT / "screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)

    app = GitHubInsightsApp(use_curl=False)
    async with app.run_test(headless=True, size=(140, 42)) as pilot:
        await pilot.pause()
        app.save_screenshot(filename="01-empty-state.svg", path=str(output_dir))

        metrics = summarize_metrics(SAMPLE_USER, SAMPLE_REPOS)
        app._render_profile(SAMPLE_USER)
        app._render_metrics(metrics)
        app._render_repositories(SAMPLE_REPOS)
        app._render_raw_preview(SAMPLE_USER, SAMPLE_REPOS)
        app._set_status("Loaded @openai. Type another handle and press Enter for next query.")
        app.query_one("#username-input", Input).value = "openai"

        await pilot.pause()
        app.save_screenshot(filename="02-user-intel.svg", path=str(output_dir))

        app.action_toggle_mode()
        app._set_status("Switched to curl mode.")
        await pilot.pause()
        app.save_screenshot(filename="03-curl-mode.svg", path=str(output_dir))


if __name__ == "__main__":
    asyncio.run(generate())
