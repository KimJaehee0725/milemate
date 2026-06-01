from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from .common import Citation, DecisionItem, RiskItem
from .stage import PrdPacket, PrdQualityReport


class PlannerReport(BaseModel):
    problem_redefinition: str
    target_users: List[str] = Field(default_factory=list)
    prioritized_kpis: List[str] = Field(default_factory=list)
    mvp_scope: List[str] = Field(default_factory=list)
    expected_value: List[str] = Field(default_factory=list)


class EngineerReport(BaseModel):
    required_data: List[str] = Field(default_factory=list)
    required_tech_blocks: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    implementation_order: List[str] = Field(default_factory=list)
    verification_plan: List[str] = Field(default_factory=list)


class FinalReportBundle(BaseModel):
    planner_report: PlannerReport
    engineer_report: EngineerReport
    prd_report: PrdPacket = Field(default_factory=PrdPacket)
    prd_quality: PrdQualityReport = Field(default_factory=PrdQualityReport)
    decision_log: List[DecisionItem] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    risks: List[RiskItem] = Field(default_factory=list)
