import asyncio

from github_insights.core.ai_insights import PydanticAIDeepInsightsGenerator
from github_insights.core.models import RepoMetrics


SAMPLE_METRICS = RepoMetrics(
    scanned_repos=1,
    total_stars=5,
    total_forks=1,
    followers=2,
    following=1,
    public_repos=1,
    score=17,
    top_language="Python",
    top_repo_name="demo",
    top_repo_stars=5,
)


def _clear_llm_env(monkeypatch) -> None:
    for key in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY", "OCTOLENS_LLM_MODEL"):
        monkeypatch.delenv(key, raising=False)


def test_defaults_to_google_model_when_google_key_present(monkeypatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_API_KEY", "google-test-key")

    generator = PydanticAIDeepInsightsGenerator()

    assert generator.model == "google-gla:gemini-2.5-flash"


def test_defaults_to_groq_model_when_only_groq_key_present(monkeypatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    generator = PydanticAIDeepInsightsGenerator()

    assert generator.model == "groq:openai/gpt-oss-120b"


def test_unprefixed_gpt_oss_model_is_mapped_to_groq(monkeypatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    monkeypatch.setenv("OCTOLENS_LLM_MODEL", "openai/gpt-oss-120b")

    generator = PydanticAIDeepInsightsGenerator()

    assert generator.model == "groq:openai/gpt-oss-120b"


def test_explicit_groq_model_reports_missing_groq_key(monkeypatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("OCTOLENS_LLM_MODEL", "groq:openai/gpt-oss-120b")
    generator = PydanticAIDeepInsightsGenerator()

    result = asyncio.run(
        generator.generate(
            username="octocat",
            user={"login": "octocat"},
            repos=[],
            metrics=SAMPLE_METRICS,
        )
    )

    assert result.status == "disabled"
    assert result.model == "groq:openai/gpt-oss-120b"
    assert result.detail == "Set GROQ_API_KEY to enable Groq LLM insights."
