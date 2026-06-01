from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StageStatus(BaseModel):
    stage_id: str
    approved: bool = False
    completed: bool = False
    summary: Optional[str] = None


class RollbackEvent(BaseModel):
    event_id: str
    from_stage: str
    target_stage: str
    reason: str = ""
    invalidated_stages: List[str] = Field(default_factory=list)
    created_at: str


class CreateSessionRequest(BaseModel):
    scenario: str = "dispatch_recommendation"
    user_input: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionState(BaseModel):
    session_id: str
    scenario: str
    current_stage: str
    approved_stages: List[str] = Field(default_factory=list)
    stage_history: List[StageStatus] = Field(default_factory=list)
    stage_outputs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    unresolved_questions: List[str] = Field(default_factory=list)
    rollback_events: List[RollbackEvent] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
