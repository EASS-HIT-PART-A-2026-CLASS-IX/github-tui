from __future__ import annotations

import os
import re
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from ..api.exceptions import GitHubApiError
from ..api.factory import create_github_client
from ..api.utils import format_iso_date
from ..core.ai_insights import PydanticAIDeepInsightsGenerator
from ..core.models import InsightsSnapshot
from ..core.service import GitHubInsightsService
from .schemas import (
    AiInsightsResponse,
    HealthResponse,
    InsightsResponse,
    RepoMetricsResponse,
    RepositoryItem,
    UserProfile,
)

TransportMode = Literal["httpx", "curl"]


def create_app() -> FastAPI:
    app = FastAPI(
        title="OctoLens API",
        version="0.1.0",
        description="HTTP API for GitHub profile and repository intelligence.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_read_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.state.deep_insights_generator = PydanticAIDeepInsightsGenerator()

    @app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get(
        "/api/v1/insights/{username}",
        response_model=InsightsResponse,
        tags=["insights"],
    )
    async def get_insights(
        username: str,
        transport: TransportMode = Query(default="httpx"),
        llm: bool = Query(
            default=False,
            description="Enable pydantic-ai deep insights powered by Gemini.",
        ),
    ) -> InsightsResponse:
        service = GitHubInsightsService(
            create_github_client(use_curl=transport == "curl"),
            deep_insights_generator=app.state.deep_insights_generator,
        )

        try:
            snapshot = await service.load_snapshot(username, include_llm=llm)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except GitHubApiError as exc:
            raise HTTPException(
                status_code=_map_github_error_status(str(exc)),
                detail=str(exc),
            ) from exc

        return _serialize_snapshot(snapshot)

    return app


def _read_cors_origins() -> list[str]:
    raw = os.getenv("OCTOLENS_CORS_ORIGINS", "http://localhost:5173")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or ["http://localhost:5173"]


def _map_github_error_status(message: str) -> int:
    match = re.search(r"HTTP (\d{3})", message)
    if match:
        return int(match.group(1))
    if "rate limit" in message.lower():
        return 429
    return 502


def _serialize_snapshot(snapshot: InsightsSnapshot) -> InsightsResponse:
    ordered_repos = sorted(
        snapshot.repos,
        key=lambda repo: (
            int(repo.get("stargazers_count") or 0),
            int(repo.get("forks_count") or 0),
        ),
        reverse=True,
    )

    return InsightsResponse(
        user=UserProfile(
            login=str(snapshot.user.get("login") or "-"),
            name=_optional_text(snapshot.user.get("name")),
            bio=_optional_text(snapshot.user.get("bio")),
            location=_optional_text(snapshot.user.get("location")),
            company=_optional_text(snapshot.user.get("company")),
            avatar_url=_optional_text(snapshot.user.get("avatar_url")),
            html_url=_optional_text(snapshot.user.get("html_url")),
            followers=int(snapshot.user.get("followers") or 0),
            following=int(snapshot.user.get("following") or 0),
            public_repos=int(snapshot.user.get("public_repos") or 0),
            joined_date=format_iso_date(_optional_text(snapshot.user.get("created_at"))),
        ),
        metrics=RepoMetricsResponse(
            scanned_repos=snapshot.metrics.scanned_repos,
            total_stars=snapshot.metrics.total_stars,
            total_forks=snapshot.metrics.total_forks,
            followers=snapshot.metrics.followers,
            following=snapshot.metrics.following,
            public_repos=snapshot.metrics.public_repos,
            score=snapshot.metrics.score,
            top_language=snapshot.metrics.top_language,
            top_repo_name=snapshot.metrics.top_repo_name,
            top_repo_stars=snapshot.metrics.top_repo_stars,
        ),
        repositories=[
            RepositoryItem(
                name=str(repo.get("name") or "-"),
                html_url=_optional_text(repo.get("html_url")),
                stars=int(repo.get("stargazers_count") or 0),
                forks=int(repo.get("forks_count") or 0),
                open_issues=int(repo.get("open_issues_count") or 0),
                language=str(repo.get("language") or "-"),
                updated_date=format_iso_date(_optional_text(repo.get("updated_at"))),
            )
            for repo in ordered_repos
        ],
        ai_insights=(
            AiInsightsResponse(
                status=snapshot.ai_insights.status,
                model=snapshot.ai_insights.model,
                summary=snapshot.ai_insights.summary,
                strengths=snapshot.ai_insights.strengths,
                risks=snapshot.ai_insights.risks,
                recommendations=snapshot.ai_insights.recommendations,
                detail=snapshot.ai_insights.detail,
            )
            if snapshot.ai_insights
            else None
        ),
    )


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


app = create_app()
