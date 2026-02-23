from github_insights.api.utils import format_iso_date, split_curl_output
from github_insights.core.metrics import calculate_score, summarize_metrics


def test_calculate_score_formula() -> None:
    score = calculate_score(
        total_stars=10,
        followers=5,
        total_forks=3,
        public_repos=2,
    )
    assert score == 45


def test_summarize_metrics_aggregates_values() -> None:
    user = {"followers": 120, "following": 9, "public_repos": 3}
    repos = [
        {"name": "alpha", "stargazers_count": 11, "forks_count": 2, "language": "Python"},
        {"name": "beta", "stargazers_count": 7, "forks_count": 5, "language": "Python"},
        {"name": "gamma", "stargazers_count": 21, "forks_count": 1, "language": "Go"},
    ]

    metrics = summarize_metrics(user, repos)

    assert metrics.scanned_repos == 3
    assert metrics.total_stars == 39
    assert metrics.total_forks == 8
    assert metrics.followers == 120
    assert metrics.top_repo_name == "gamma"
    assert metrics.top_repo_stars == 21
    assert metrics.top_language == "Python"
    assert metrics.score == 368


def test_split_curl_output_returns_body_and_status() -> None:
    body, status = split_curl_output('{"ok":true}\n200')
    assert body == '{"ok":true}'
    assert status == 200


def test_format_iso_date_handles_valid_and_invalid_values() -> None:
    assert format_iso_date("2024-06-15T12:30:00Z") == "2024-06-15"
    assert format_iso_date("not-a-date") == "-"
    assert format_iso_date(None) == "-"
