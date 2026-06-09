from __future__ import annotations

from typing import Dict, List, Literal

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


ReportExportFormat = Literal["docx", "pdf", "pptx"]
ReportSectionTone = Literal["neutral", "decision", "ready", "warning", "risk", "technical"]


class ReportSummaryCard(BaseModel):
    title: str
    value: str
    detail: str = ""
    tone: ReportSectionTone = "neutral"


class ReportSection(BaseModel):
    title: str
    body: str = ""
    items: List[str] = Field(default_factory=list)
    rows: List[Dict[str, str]] = Field(default_factory=list)
    tone: ReportSectionTone = "neutral"


class ReportDocumentModel(BaseModel):
    title: str
    subtitle: str
    audience: str
    summary: str
    document_id: str = ""
    version: str = ""
    created_on: str = ""
    prepared_by: str = ""
    review_status: str = ""
    review_score: int = 0
    review_findings: List[str] = Field(default_factory=list)
    cards: List[ReportSummaryCard] = Field(default_factory=list)
    sections: List[ReportSection] = Field(default_factory=list)
    risks: List[RiskItem] = Field(default_factory=list)
    decisions: List[DecisionItem] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
