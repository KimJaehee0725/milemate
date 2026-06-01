"""Session API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.backend.api.errors import raise_stage_http_error
from app.backend.api.state import get_stage_manager
from app.backend.core.stage_manager import StageManager, StageTransitionError
from app.backend.schemas.session import CreateSessionRequest, SessionState

router = APIRouter(tags=["sessions"])


@router.post("/sessions", response_model=SessionState, status_code=201)
def create_session(
    request: CreateSessionRequest,
    stage_manager: StageManager = Depends(get_stage_manager),
) -> SessionState:
    try:
        return stage_manager.create_session(
            scenario=request.scenario,
            user_input=request.user_input,
            metadata=request.metadata,
        )
    except StageTransitionError as exc:
        raise_stage_http_error(exc)


@router.get("/sessions/{session_id}", response_model=SessionState)
def get_session(
    session_id: str,
    stage_manager: StageManager = Depends(get_stage_manager),
) -> SessionState:
    try:
        return stage_manager.get_session(session_id)
    except StageTransitionError as exc:
        raise_stage_http_error(exc)
