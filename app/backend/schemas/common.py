from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    UNKNOWN_SESSION = "unknown_session"
    UNKNOWN_SCENARIO = "unknown_scenario"
    INVALID_STAGE_TRANSITION = "invalid_stage_transition"
    REPORT_NOT_READY = "report_not_ready"


class StageRunStatus(str, Enum):
    COMPLETED = "completed"
    WARNING = "warning"
    BLOCKED = "blocked"


class Citation(BaseModel):
    source_type: str
    title: str
    locator: str
    relevance_note: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DecisionItem(BaseModel):
    item: str
    status: Literal["proposed", "approved", "deferred", "rejected"]
    rationale: Optional[str] = None


class RiskItem(BaseModel):
    category: Literal["data", "technical", "operational", "regulatory", "scope", "other"]
    severity: Literal["low", "medium", "high"] = "medium"
    description: str
    mitigation: Optional[str] = None
