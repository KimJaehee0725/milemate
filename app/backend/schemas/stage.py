from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .common import Citation, DecisionItem, RiskItem


class StageRequest(BaseModel):
    session_id: str
    stage_id: str
    scenario: str
    user_input: str
    context: Dict[str, Any] = Field(default_factory=dict)


class RollbackRequest(BaseModel):
    session_id: str
    target_stage: str
    reason: str


class StageOutputBundle(BaseModel):
    summary: str
    planner_view: Dict[str, Any] = Field(default_factory=dict)
    engineer_view: Dict[str, Any] = Field(default_factory=dict)
    decision_points: List[DecisionItem] = Field(default_factory=list)
    required_user_input: List[str] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    risks: List[RiskItem] = Field(default_factory=list)
    rollback_targets: List[str] = Field(default_factory=list)


class StageResponse(BaseModel):
    session_id: str
    stage_id: str
    status: str
    output: StageOutputBundle
