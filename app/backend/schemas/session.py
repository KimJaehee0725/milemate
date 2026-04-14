from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class StageStatus(BaseModel):
    stage_id: str
    approved: bool = False
    completed: bool = False
    summary: Optional[str] = None


class SessionState(BaseModel):
    session_id: str
    scenario: str
    current_stage: str
    approved_stages: List[str] = Field(default_factory=list)
    stage_history: List[StageStatus] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)
