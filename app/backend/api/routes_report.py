"""Final report API route."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response

from app.backend.api.errors import raise_stage_http_error
from app.backend.api.state import get_orchestrator
from app.backend.core.config_loader import load_app_config
from app.backend.core.orchestrator import Orchestrator
from app.backend.core.stage_manager import StageTransitionError
from app.backend.schemas.report import FinalReportBundle
from app.backend.services.report_export_service import (
    ReportExportMeta,
    ReportExportService,
    UnsupportedReportExportError,
)

router = APIRouter(tags=["reports"])
export_service = ReportExportService()


def _build_export_meta(session_id: str) -> ReportExportMeta:
    report_cfg = load_app_config().report
    created_on = date.today().isoformat()
    return ReportExportMeta(
        document_id=f"PLN-{created_on}-{session_id[:8]}",
        version=report_cfg.version,
        created_on=created_on,
        prepared_by=report_cfg.prepared_by,
    )


@router.get("/reports/{session_id}", response_model=FinalReportBundle)
def get_report(
    session_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> FinalReportBundle:
    try:
        return orchestrator.build_final_report(session_id)
    except StageTransitionError as exc:
        raise_stage_http_error(exc)


@router.get("/reports/{session_id}/exports/{export_format}")
def get_report_export(
    session_id: str,
    export_format: str,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> Response:
    try:
        report = orchestrator.build_final_report(session_id)
        exported = export_service.export(report, export_format, _build_export_meta(session_id))
    except UnsupportedReportExportError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "unsupported_report_export",
                "message": str(exc),
            },
        ) from exc
    except StageTransitionError as exc:
        raise_stage_http_error(exc)

    return Response(
        content=exported.content,
        media_type=exported.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{exported.filename}"',
        },
    )
