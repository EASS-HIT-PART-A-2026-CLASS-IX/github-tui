import argparse
from .ui.app import GitHubInsightsApp

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OctoLens GitHub TUI")
    parser.add_argument(
        "--curl",
        action="store_true",
        help="Use curl for API requests instead of httpx.",
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    app = GitHubInsightsApp(use_curl=args.curl)
    app.run()

if __name__ == "__main__":
    main()
