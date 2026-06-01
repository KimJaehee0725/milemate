"""Stage execution API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.backend.api.errors import raise_bad_request, raise_stage_http_error
from app.backend.api.state import get_orchestrator
from app.backend.core.orchestrator import Orchestrator
from app.backend.core.stage_manager import StageTransitionError
from app.backend.schemas.session import SessionState
from app.backend.schemas.stage import (
    ApproveStageRequest,
    RollbackRequest,
    RunStageRequest,
    StageResponse,
)

router = APIRouter(tags=["stages"])


@router.post("/stages/run", response_model=StageResponse)
def run_stage(
    request: RunStageRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> StageResponse:
    try:
        return orchestrator.run_current_stage(
            session_id=request.session_id,
            user_input=request.user_input,
            context=request.context,
        )
    except StageTransitionError as exc:
        raise_stage_http_error(exc)
    except ValueError as exc:
        raise_bad_request(str(exc))


@router.post("/stages/approve", response_model=SessionState)
def approve_stage(
    request: ApproveStageRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> SessionState:
    try:
        return orchestrator.approve_current_stage(
            session_id=request.session_id,
            stage_id=request.stage_id,
        )
    except StageTransitionError as exc:
        raise_stage_http_error(exc)


@router.post("/stages/rollback", response_model=SessionState)
def rollback_stage(
    request: RollbackRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> SessionState:
    try:
        return orchestrator.rollback(
            session_id=request.session_id,
            target_stage=request.target_stage,
            reason=request.reason,
        )
    except StageTransitionError as exc:
        raise_stage_http_error(exc)
