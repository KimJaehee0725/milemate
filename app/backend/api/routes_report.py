"""Final report API route."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.backend.api.errors import raise_stage_http_error
from app.backend.api.state import get_orchestrator
from app.backend.core.orchestrator import Orchestrator
from app.backend.core.stage_manager import StageTransitionError
from app.backend.schemas.report import FinalReportBundle

router = APIRouter(tags=["reports"])


@router.get("/reports/{session_id}", response_model=FinalReportBundle)
def get_report(
    session_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> FinalReportBundle:
    try:
        return orchestrator.build_final_report(session_id)
    except StageTransitionError as exc:
        raise_stage_http_error(exc)
