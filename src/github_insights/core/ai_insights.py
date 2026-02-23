from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.groq import GroqProvider

from .models import AIInsights, RepoMetrics

ProviderName = Literal["google-gla", "groq"]

DEFAULT_GOOGLE_MODEL_NAME = "gemini-2.5-flash"
DEFAULT_GROQ_MODEL_NAME = "openai/gpt-oss-120b"
DEFAULT_GOOGLE_MODEL = f"google-gla:{DEFAULT_GOOGLE_MODEL_NAME}"
DEFAULT_GROQ_MODEL = f"groq:{DEFAULT_GROQ_MODEL_NAME}"


class _DeepInsightsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=20, max_length=700)
    strengths: list[str] = Field(default_factory=list, max_length=4)
    risks: list[str] = Field(default_factory=list, max_length=3)
    recommendations: list[str] = Field(default_factory=list, max_length=4)


@dataclass(frozen=True, slots=True)
class _LLMConfig:
    provider: ProviderName
    model_name: str
    api_key: str | None
    model: str


class PydanticAIDeepInsightsGenerator:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        enabled: bool | None = None,
    ) -> None:
        llm_config = _resolve_llm_config(
            model=model or os.getenv("OCTOLENS_LLM_MODEL"),
            api_key_override=_read_secret(api_key),
            google_api_key=(
                _read_secret(os.getenv("GOOGLE_API_KEY")) or _read_secret(os.getenv("GEMINI_API_KEY"))
            ),
            groq_api_key=_read_secret(os.getenv("GROQ_API_KEY")),
        )
        self.model = llm_config.model
        self._provider = llm_config.provider
        self._api_key = llm_config.api_key
        self._enabled = _resolve_enabled(enabled)
        self._agent: Agent[None, _DeepInsightsOutput] | None = None

    async def generate(
        self,
        *,
        username: str,
        user: dict[str, Any],
        repos: list[dict[str, Any]],
        metrics: RepoMetrics,
    ) -> AIInsights:
        if not self._enabled:
            return AIInsights(
                status="disabled",
                model=self.model,
                detail="LLM insights are disabled by configuration.",
            )

        if not self._api_key:
            missing_key_hint = (
                "Set GOOGLE_API_KEY (or GEMINI_API_KEY) to enable Google LLM insights."
                if self._provider == "google-gla"
                else "Set GROQ_API_KEY to enable Groq LLM insights."
            )
            return AIInsights(
                status="disabled",
                model=self.model,
                detail=missing_key_hint,
            )

        if self._agent is None:
            self._agent = self._build_agent()

        try:
            result = await self._agent.run(_build_prompt(username, user, repos, metrics))
        except Exception:
            return AIInsights(
                status="error",
                model=self.model,
                detail="LLM request failed. Check API key, quota, and model settings.",
            )

        output = result.output
        return AIInsights(
            status="ready",
            model=self.model,
            summary=output.summary.strip(),
            strengths=_clean_lines(output.strengths, limit=4),
            risks=_clean_lines(output.risks, limit=3),
            recommendations=_clean_lines(output.recommendations, limit=4),
        )

    def _build_agent(self) -> Agent[None, _DeepInsightsOutput]:
        if self._provider == "google-gla":
            provider = GoogleProvider(api_key=self._api_key)
            llm_model = GoogleModel(self.model.split(":", 1)[1], provider=provider)
        else:
            provider = GroqProvider(api_key=self._api_key)
            llm_model = GroqModel(self.model.split(":", 1)[1], provider=provider)

        return Agent(
            model=llm_model,
            output_type=_DeepInsightsOutput,
            system_prompt=(
                "You are OctoLens AI, a GitHub analytics copilot. "
                "Use only the provided snapshot. Be concise, practical, and data-driven. "
                "Do not invent external facts."
            ),
            retries=1,
        )


def _build_prompt(
    username: str,
    user: dict[str, Any],
    repos: list[dict[str, Any]],
    metrics: RepoMetrics,
) -> str:
    ranked_repos = sorted(
        repos,
        key=lambda repo: (
            int(repo.get("stargazers_count") or 0),
            int(repo.get("forks_count") or 0),
            int(repo.get("open_issues_count") or 0),
        ),
        reverse=True,
    )[:8]

    lines = [
        f"GitHub account: @{username}",
        "Create deep insights for an engineering dashboard.",
        "",
        "Profile:",
        f"- Display name: {user.get('name') or '-'}",
        f"- Bio: {user.get('bio') or '-'}",
        f"- Location: {user.get('location') or '-'}",
        f"- Company: {user.get('company') or '-'}",
        f"- Followers: {metrics.followers}",
        f"- Following: {metrics.following}",
        f"- Public repos: {metrics.public_repos}",
        "",
        "Computed metrics:",
        f"- Scanned repos: {metrics.scanned_repos}",
        f"- Total stars: {metrics.total_stars}",
        f"- Total forks: {metrics.total_forks}",
        f"- Top language: {metrics.top_language}",
        f"- Top repo: {metrics.top_repo_name} ({metrics.top_repo_stars} stars)",
        f"- Composite score: {metrics.score}",
        "",
        "Top repositories:",
    ]

    if ranked_repos:
        for idx, repo in enumerate(ranked_repos, start=1):
            lines.append(
                (
                    f"{idx}. {repo.get('name') or '-'} | "
                    f"stars={int(repo.get('stargazers_count') or 0)} | "
                    f"forks={int(repo.get('forks_count') or 0)} | "
                    f"open_issues={int(repo.get('open_issues_count') or 0)} | "
                    f"language={repo.get('language') or '-'}"
                )
            )
    else:
        lines.append("No public repositories found.")

    lines.extend(
        [
            "",
            "Requirements:",
            "- Keep summary under 120 words.",
            "- Strengths and risks must reference the provided data.",
            "- Recommendations must be practical and specific.",
        ]
    )
    return "\n".join(lines)


def _resolve_llm_config(
    *,
    model: str | None,
    api_key_override: str | None,
    google_api_key: str | None,
    groq_api_key: str | None,
) -> _LLMConfig:
    provider_hint, model_hint = _parse_model(model)
    provider = provider_hint or _infer_provider(model_hint, google_api_key=google_api_key, groq_api_key=groq_api_key)
    model_name = model_hint or _default_model_name(provider)
    api_key = api_key_override or (google_api_key if provider == "google-gla" else groq_api_key)
    return _LLMConfig(
        provider=provider,
        model_name=model_name,
        api_key=api_key,
        model=f"{provider}:{model_name}",
    )


def _parse_model(model: str | None) -> tuple[ProviderName | None, str | None]:
    cleaned = (model or "").strip()
    if not cleaned:
        return None, None

    if ":" not in cleaned:
        return None, cleaned

    prefix, _, model_name = cleaned.partition(":")
    normalized_prefix = prefix.strip().lower()
    model_name = model_name.strip()
    if not model_name:
        return None, None

    if normalized_prefix in {"google", "google-gla", "gemini"}:
        return "google-gla", model_name
    if normalized_prefix == "groq":
        return "groq", model_name

    # Preserve unknown prefixes in the model name and infer provider from model/key context.
    return None, cleaned


def _infer_provider(
    model_name: str | None,
    *,
    google_api_key: str | None,
    groq_api_key: str | None,
) -> ProviderName:
    normalized_name = (model_name or "").strip().lower()
    if "gemini" in normalized_name or normalized_name.startswith("models/"):
        return "google-gla"
    if (
        normalized_name.startswith("openai/")
        or normalized_name.startswith("llama")
        or normalized_name.startswith("qwen/")
        or normalized_name.startswith("whisper")
        or normalized_name.startswith("moonshotai/")
        or "gpt-oss" in normalized_name
    ):
        return "groq"
    if google_api_key:
        return "google-gla"
    if groq_api_key:
        return "groq"
    return "google-gla"


def _default_model_name(provider: ProviderName) -> str:
    if provider == "groq":
        return DEFAULT_GROQ_MODEL_NAME
    return DEFAULT_GOOGLE_MODEL_NAME


def _read_secret(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _resolve_enabled(enabled: bool | None) -> bool:
    if enabled is not None:
        return enabled

    raw = os.getenv("OCTOLENS_LLM_ENABLED", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _clean_lines(items: list[str], *, limit: int) -> list[str]:
    cleaned: list[str] = []
    for item in items:
        text = item.strip()
        if text:
            cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned
