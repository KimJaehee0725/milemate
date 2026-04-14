from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class Citation(BaseModel):
    source_type: str
    title: str
    locator: str
    relevance_note: str


class DecisionItem(BaseModel):
    item: str
    status: Literal["proposed", "approved", "deferred", "rejected"]
    rationale: Optional[str] = None


class RiskItem(BaseModel):
    category: Literal["data", "technical", "operational", "regulatory", "scope", "other"]
    severity: Literal["low", "medium", "high"] = "medium"
    description: str
    mitigation: Optional[str] = None
