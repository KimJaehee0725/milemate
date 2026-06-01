"""HTTP error mapping for backend workflow errors."""

from __future__ import annotations

from fastapi import HTTPException

from app.backend.core.stage_manager import StageTransitionError
from app.backend.schemas.common import ErrorCode

_STATUS_BY_CODE = {
    ErrorCode.UNKNOWN_SESSION: 404,
    ErrorCode.UNKNOWN_SCENARIO: 400,
    ErrorCode.INVALID_STAGE_TRANSITION: 400,
    ErrorCode.REPORT_NOT_READY: 400,
    ErrorCode.MODEL_NOT_CONFIGURED: 503,
    ErrorCode.MODEL_CALL_FAILED: 502,
    ErrorCode.MODEL_OUTPUT_INVALID: 502,
}


def raise_stage_http_error(exc: StageTransitionError) -> None:
    raise HTTPException(
        status_code=_STATUS_BY_CODE.get(exc.error_code, 400),
        detail={"code": exc.error_code.value, "message": str(exc)},
    ) from exc


def raise_bad_request(message: str) -> None:
    raise HTTPException(
        status_code=400,
        detail={"code": ErrorCode.INVALID_STAGE_TRANSITION.value, "message": message},
    )
