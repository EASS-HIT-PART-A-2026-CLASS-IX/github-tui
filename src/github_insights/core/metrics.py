from collections import Counter
from typing import Any
from .models import RepoMetrics

def calculate_score(
    *, total_stars: int, followers: int, total_forks: int, public_repos: int
) -> int:
    return (total_stars * 3) + (followers * 2) + total_forks + public_repos

def summarize_metrics(user: dict[str, Any], repos: list[dict[str, Any]]) -> RepoMetrics:
    total_stars = sum(int(repo.get("stargazers_count") or 0) for repo in repos)
    total_forks = sum(int(repo.get("forks_count") or 0) for repo in repos)
    followers = int(user.get("followers") or 0)
    following = int(user.get("following") or 0)
    public_repos = int(user.get("public_repos") or len(repos))

    languages = Counter(
        repo.get("language") for repo in repos if repo.get("language") is not None
    )
    top_language = languages.most_common(1)[0][0] if languages else "-"

    top_repo = max(
        repos,
        key=lambda repo: int(repo.get("stargazers_count") or 0),
        default={},
    )
    top_repo_name = str(top_repo.get("name") or "-")
    top_repo_stars = int(top_repo.get("stargazers_count") or 0)

    return RepoMetrics(
        scanned_repos=len(repos),
        total_stars=total_stars,
        total_forks=total_forks,
        followers=followers,
        following=following,
        public_repos=public_repos,
        score=calculate_score(
            total_stars=total_stars,
            followers=followers,
            total_forks=total_forks,
            public_repos=public_repos,
        ),
        top_language=top_language,
        top_repo_name=top_repo_name,
        top_repo_stars=top_repo_stars,
    )
