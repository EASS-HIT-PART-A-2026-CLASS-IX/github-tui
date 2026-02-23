from __future__ import annotations

import json
from typing import Any

from rich.panel import Panel
from rich.table import Table
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, RichLog, Static

from ..api.exceptions import GitHubApiError
from ..api.factory import create_github_client
from ..api.utils import format_iso_date
from ..core.models import RepoMetrics
from ..core.service import GitHubInsightsService


class GitHubInsightsApp(App[None]):
    TITLE = "OctoLens"
    SUB_TITLE = "GitHub intelligence in your terminal"

    CSS = """
    Screen {
        background: #f5f5f7;
        color: #1d1d1f;
    }

    #app-shell {
        height: 1fr;
        padding: 0;
    }

    #topbar {
        height: 3;
        background: #ffffff;
        color: #1d1d1f;
        border-bottom: solid #d2d2d7;
        content-align: center middle;
        text-style: bold italic;
    }

    #toolbar {
        height: 3;
        padding: 0 1;
        background: #f5f5f7;
    }

    #username-input {
        width: 1fr;
        margin-right: 1;
        background: #ffffff;
        color: #1d1d1f;
        border: solid #d2d2d7;
    }

    Button {
        min-width: 12;
        margin-right: 1;
        background: #ffffff;
        color: #0071e3;
        border: solid #d2d2d7;
    }

    Button.-active,
    Button:hover {
        background: #eef5ff;
    }

    #query-guide {
        height: 2;
        background: #ffffff;
        color: #3a3a3c;
        border-top: solid #d2d2d7;
        border-bottom: solid #d2d2d7;
        content-align: left middle;
        padding: 0 1;
    }

    #content {
        height: 1fr;
        padding: 1;
    }

    #left-pane {
        width: 42;
        border: solid #d2d2d7;
        background: #ffffff;
        padding: 1;
        margin-right: 1;
    }

    #right-pane {
        width: 1fr;
        border: solid #d2d2d7;
        background: #ffffff;
        padding: 1;
    }

    #profile {
        height: 12;
        border: solid #d2d2d7;
        padding: 0 1;
        background: #fbfbfd;
    }

    .metric-row {
        height: 4;
        margin-top: 1;
    }

    .metric {
        width: 1fr;
        border: solid #d2d2d7;
        padding: 0 1;
        margin-right: 1;
        content-align: center middle;
        background: #fbfbfd;
    }

    #highlights {
        margin-top: 1;
        height: 8;
        border: solid #d2d2d7;
        padding: 0 1;
        background: #fbfbfd;
    }

    #query-help {
        margin-top: 1;
        height: 8;
        border: solid #d2d2d7;
        padding: 0 1;
        background: #fbfbfd;
        color: #1d1d1f;
    }

    #matrix-title {
        height: 1;
        margin-bottom: 1;
        background: #0071e3;
        color: #ffffff;
        text-style: bold;
        content-align: left middle;
        padding: 0 1;
    }

    #repos-table {
        height: 16;
        border: solid #d2d2d7;
        background: #ffffff;
        color: #1d1d1f;
    }

    #raw-title {
        height: 1;
        margin-top: 1;
        margin-bottom: 1;
        background: #0071e3;
        color: #ffffff;
        text-style: bold;
        content-align: left middle;
        padding: 0 1;
    }

    #raw-json {
        height: 15;
        border: solid #d2d2d7;
        background: #ffffff;
        color: #1d1d1f;
    }

    #status {
        height: 1;
        padding: 0 1 0 1;
        background: #ffffff;
        color: #1d1d1f;
        border-top: solid #d2d2d7;
    }

    #command-hints {
        height: 1;
        padding: 0 1;
        background: #f5f5f7;
        color: #6e6e73;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("f", "fetch_user", "Fetch"),
        Binding("c", "toggle_mode", "Toggle HTTP/CURL"),
        Binding("/", "focus_input", "Focus Input"),
        Binding("n", "new_query", "New Query"),
        Binding("r", "clear_view", "Clear"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, *, use_curl: bool = False) -> None:
        super().__init__()
        self.use_curl = use_curl
        self.service = self._build_service()
        self._loading = False

    def compose(self) -> ComposeResult:
        with Vertical(id="app-shell"):
            yield Static("OctoLens  •  GitHub Terminal Intelligence", id="topbar")
            with Horizontal(id="toolbar"):
                yield Input(
                    placeholder="Type GitHub handle, then press Enter (example: aws, torvalds, openai)",
                    id="username-input",
                )
                yield Button("Fetch", id="fetch-btn")
                yield Button("Clear", id="clear-btn")
                yield Button(self._mode_label(), id="mode-btn")
            yield Static(
                "To run another query: type a new handle in the input and press Enter. No reset needed.",
                id="query-guide",
            )

            with Horizontal(id="content"):
                with Vertical(id="left-pane"):
                    yield Static("Enter a handle and press Enter or Fetch.", id="profile")
                    with Horizontal(classes="metric-row"):
                        yield Static("Total Stars\n0", classes="metric", id="stars-metric")
                        yield Static("Total Forks\n0", classes="metric", id="forks-metric")
                    with Horizontal(classes="metric-row"):
                        yield Static("Followers\n0", classes="metric", id="followers-metric")
                        yield Static("Score\n0", classes="metric", id="score-metric")
                    yield Static("No highlights yet.", id="highlights")
                    yield Static(
                        "[b #0071e3]Query flow[/b #0071e3]\n"
                        "1) Type handle in the top input\n"
                        "2) Press Enter (or click Fetch)\n"
                        "3) For another user, replace handle and press Enter again\n"
                        "Shortcuts: / focus input, N new query, C transport mode.",
                        id="query-help",
                    )

                with Vertical(id="right-pane"):
                    yield Static(" Repository Metrics ", id="matrix-title")
                    yield DataTable(id="repos-table")
                    yield Static(" Raw API Preview ", id="raw-title")
                    yield RichLog(id="raw-json", wrap=False, auto_scroll=False)

            yield Static("Ready.", id="status")
            yield Static(
                "Enter: Fetch | /: Focus input | N: New query | C: Toggle mode | R: Clear | Q: Quit",
                id="command-hints",
            )

    def on_mount(self) -> None:
        table = self.query_one("#repos-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns("Repository", "Stars", "Forks", "Issues", "Language", "Updated")
        self.query_one("#username-input", Input).focus()

    def action_toggle_mode(self) -> None:
        self.use_curl = not self.use_curl
        self.service = self._build_service()
        self.query_one("#mode-btn", Button).label = self._mode_label()
        self._set_status(
            f"Switched to {'curl' if self.use_curl else 'httpx'} mode."
        )

    def action_focus_input(self) -> None:
        self.query_one("#username-input", Input).focus()
        self._set_status("Input focused. Type a handle and press Enter.")

    def action_new_query(self) -> None:
        input_widget = self.query_one("#username-input", Input)
        input_widget.value = ""
        input_widget.focus()
        self._set_status("Start a new query: type a handle and press Enter.")

    def action_clear_view(self) -> None:
        self._clear_view()

    async def action_fetch_user(self) -> None:
        await self._load_user_from_input()

    @on(Button.Pressed, "#fetch-btn")
    async def on_fetch_pressed(self) -> None:
        await self._load_user_from_input()

    @on(Input.Submitted, "#username-input")
    async def on_input_submitted(self) -> None:
        await self._load_user_from_input()

    @on(Button.Pressed, "#clear-btn")
    def on_clear_pressed(self) -> None:
        self._clear_view()

    @on(Button.Pressed, "#mode-btn")
    def on_mode_pressed(self) -> None:
        self.action_toggle_mode()

    async def _load_user_from_input(self) -> None:
        username = self.query_one("#username-input", Input).value.strip()
        if not username:
            self._set_status("Please enter a GitHub handle.", error=True)
            return

        if self._loading:
            return

        self._loading = True
        fetch_btn = self.query_one("#fetch-btn", Button)
        fetch_btn.disabled = True
        self._set_status(
            f"Loading @{username} with {'curl' if self.use_curl else 'httpx'}..."
        )

        try:
            snapshot = await self.service.load_snapshot(username)
        except (GitHubApiError, ValueError) as exc:
            self._set_status(str(exc), error=True)
            return
        finally:
            fetch_btn.disabled = False
            self._loading = False

        user = snapshot.user
        repos = snapshot.repos
        metrics = snapshot.metrics
        self._render_profile(user)
        self._render_metrics(metrics)
        self._render_repositories(repos)
        self._render_raw_preview(user, repos)
        self.query_one("#username-input", Input).focus()
        self._set_status(
            f"Loaded @{user.get('login', username)}. Type another handle and press Enter for next query."
        )

    def _render_profile(self, user: dict[str, Any]) -> None:
        grid = Table.grid(expand=True)
        grid.add_column(style="bold #0071e3", no_wrap=True)
        grid.add_column(style="#1d1d1f")

        name = user.get("name") or "-"
        login = user.get("login") or "-"
        bio = user.get("bio") or "No bio provided."
        grid.add_row("Name", str(name))
        grid.add_row("Handle", f"@{login}")
        grid.add_row("Location", str(user.get("location") or "-"))
        grid.add_row("Company", str(user.get("company") or "-"))
        grid.add_row("Joined", format_iso_date(user.get("created_at")))
        grid.add_row("Profile", str(user.get("html_url") or "-"))

        panel = Panel.fit(grid, title=" Profile ", border_style="#0071e3")
        self.query_one("#profile", Static).update(panel)

        if bio and bio != "No bio provided.":
            self.query_one("#highlights", Static).update(
                Panel(str(bio), title=" Highlights ", border_style="#0071e3")
            )

    def _render_metrics(self, metrics: RepoMetrics) -> None:
        self.query_one("#stars-metric", Static).update(
            f"[bold #0071e3]Total Stars[/bold #0071e3]\n[bold #1d1d1f]{metrics.total_stars}[/bold #1d1d1f]"
        )
        self.query_one("#forks-metric", Static).update(
            f"[bold #0071e3]Total Forks[/bold #0071e3]\n[bold #1d1d1f]{metrics.total_forks}[/bold #1d1d1f]"
        )
        self.query_one("#followers-metric", Static).update(
            f"[bold #0071e3]Followers[/bold #0071e3]\n[bold #1d1d1f]{metrics.followers}[/bold #1d1d1f]"
        )
        self.query_one("#score-metric", Static).update(
            f"[bold #0071e3]Score[/bold #0071e3]\n[bold #1d1d1f]{metrics.score}[/bold #1d1d1f]"
        )

        highlights = (
            f"[bold #0071e3]Top language:[/bold #0071e3] {metrics.top_language}\n"
            f"[bold #0071e3]Top repo:[/bold #0071e3] {metrics.top_repo_name} ({metrics.top_repo_stars} stars)\n"
            f"[bold #0071e3]Public repos:[/bold #0071e3] {metrics.public_repos}\n"
            f"[bold #0071e3]Following:[/bold #0071e3] {metrics.following}\n"
            f"[bold #0071e3]Scanned repos:[/bold #0071e3] {metrics.scanned_repos}"
        )
        self.query_one("#highlights", Static).update(
            Panel(highlights, title=" Highlights ", border_style="#0071e3")
        )

    def _render_repositories(self, repos: list[dict[str, Any]]) -> None:
        table = self.query_one("#repos-table", DataTable)
        table.clear()

        ordered = sorted(
            repos,
            key=lambda repo: (
                int(repo.get("stargazers_count") or 0),
                int(repo.get("forks_count") or 0),
            ),
            reverse=True,
        )
        for repo in ordered:
            table.add_row(
                str(repo.get("name") or "-"),
                str(int(repo.get("stargazers_count") or 0)),
                str(int(repo.get("forks_count") or 0)),
                str(int(repo.get("open_issues_count") or 0)),
                str(repo.get("language") or "-"),
                format_iso_date(repo.get("updated_at")),
            )

        if not ordered:
            table.add_row("-", "0", "0", "0", "-", "-")

    def _render_raw_preview(self, user: dict[str, Any], repos: list[dict[str, Any]]) -> None:
        preview = {
            "user": {
                "login": user.get("login"),
                "name": user.get("name"),
                "html_url": user.get("html_url"),
                "followers": user.get("followers"),
                "following": user.get("following"),
                "public_repos": user.get("public_repos"),
            },
            "top_repositories": [
                {
                    "name": repo.get("name"),
                    "stargazers_count": repo.get("stargazers_count"),
                    "forks_count": repo.get("forks_count"),
                    "language": repo.get("language"),
                    "html_url": repo.get("html_url"),
                }
                for repo in sorted(
                    repos,
                    key=lambda item: int(item.get("stargazers_count") or 0),
                    reverse=True,
                )[:5]
            ],
        }
        raw_widget = self.query_one("#raw-json", RichLog)
        raw_widget.clear()
        raw_widget.write("[bold #0071e3]Raw JSON preview[/bold #0071e3]")
        raw_widget.write(json.dumps(preview, indent=2))

    def _clear_view(self) -> None:
        self.query_one("#profile", Static).update("Enter a handle and press Enter or Fetch.")
        self.query_one("#stars-metric", Static).update("Total Stars\n0")
        self.query_one("#forks-metric", Static).update("Total Forks\n0")
        self.query_one("#followers-metric", Static).update("Followers\n0")
        self.query_one("#score-metric", Static).update("Score\n0")
        self.query_one("#highlights", Static).update("No highlights yet.")
        self.query_one("#repos-table", DataTable).clear()
        raw_widget = self.query_one("#raw-json", RichLog)
        raw_widget.clear()
        self.query_one("#username-input", Input).focus()
        self._set_status("Cleared. Type a handle and press Enter.")

    def _set_status(self, message: str, *, error: bool = False) -> None:
        if error:
            self.query_one("#status", Static).update(
                f"[bold #ff3b30]Error:[/bold #ff3b30] {message}"
            )
            return
        self.query_one("#status", Static).update(
            f"[bold #34c759]Status:[/bold #34c759] {message}"
        )

    def _mode_label(self) -> str:
        return f"Mode: {('curl' if self.use_curl else 'httpx')}"

    def _build_service(self) -> GitHubInsightsService:
        client = create_github_client(use_curl=self.use_curl)
        return GitHubInsightsService(client)
