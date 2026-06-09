"""Runtime readiness API routes."""

from __future__ import annotations

import shutil

from fastapi import APIRouter, Request

from app.backend.core.config_loader import RootConfig
from app.backend.schemas.session import RuntimeStatusResponse

router = APIRouter(prefix="/runtime", tags=["runtime"])


@router.get("/status", response_model=RuntimeStatusResponse)
def get_runtime_status(request: Request) -> RuntimeStatusResponse:
    config: RootConfig = request.app.state.config
    cli_path = shutil.which(config.serving.cli_binary)
    return RuntimeStatusResponse(
        app_name=config.app.name,
        api_mode=config.model.api_style,
        runtime_mode=_runtime_mode_label(config),
        serving_engine=config.serving.engine,
        model_id=config.model.model_id,
        reasoning_effort=config.model.reasoning_effort,
        cli_binary=config.serving.cli_binary,
        cli_available=cli_path is not None,
        cli_path=cli_path,
        timeout=config.serving.request_timeout_seconds,
    )


def _runtime_mode_label(config: RootConfig) -> str:
    if not config.features.use_codex_generation:
        return "local_demo"
    if config.features.allow_deterministic_fallback:
        return f"{config.serving.engine}_with_fallback"
    return f"live_{config.serving.engine}"
