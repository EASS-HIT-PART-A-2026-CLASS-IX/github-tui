# github-tui

**OctoLens** is a clean, keyboard-first GitHub TUI for profile and repository intelligence.

## Preview

![Empty state](screenshots/01-empty-state.svg)
![User intel view](screenshots/02-user-intel.svg)
![Curl transport mode](screenshots/03-curl-mode.svg)

## Features

- profile card by GitHub handle
- stars, forks, followers, and score metrics
- repository matrix sorted by impact
- raw JSON panel for quick API inspection
- transport toggle: `httpx` or real `curl`

## Quick start

```bash
uv sync
uv run python main.py
```

```bash
uv run python main.py --curl
```

## Keys

- `Enter` / `f`: fetch
- `/`: focus input
- `n`: new query
- `c`: toggle `httpx` / `curl`
- `r`: clear
- `q`: quit

## Dev

```bash
uv run pytest -q
uv run python scripts/generate_readme_screenshots.py
```
