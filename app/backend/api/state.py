"""FastAPI dependency accessors for app-scoped runtime objects."""

from fastapi import Request

from app.backend.core.orchestrator import Orchestrator
from app.backend.core.stage_manager import StageManager


def get_stage_manager(request: Request) -> StageManager:
    return request.app.state.stage_manager


def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator
