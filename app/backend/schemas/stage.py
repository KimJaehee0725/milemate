from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import Citation, DecisionItem, RiskItem, StageRunStatus


class StrictStageModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PrdProblem(StrictStageModel):
    customer_pain: str = ""
    business_impact: str = ""
    current_workaround: str = ""
    success_criteria: List[str] = Field(default_factory=list)


class PrdPersona(StrictStageModel):
    name: str = ""
    role: str = ""
    needs: List[str] = Field(default_factory=list)


class PrdScope(StrictStageModel):
    in_scope: List[str] = Field(default_factory=list)
    out_of_scope: List[str] = Field(default_factory=list)


class PrdScreenSpec(StrictStageModel):
    name: str = ""
    purpose: str = ""
    primary_user: str = ""
    entry_point: str = ""
    components: List[str] = Field(default_factory=list)
    primary_actions: List[str] = Field(default_factory=list)
    empty_states: List[str] = Field(default_factory=list)
    error_states: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)


class PrdPolicyRule(StrictStageModel):
    name: str = ""
    trigger: str = ""
    rule: str = ""
    owner: str = ""
    exception_handling: str = ""


class PrdMetric(StrictStageModel):
    name: str = ""
    baseline: str = ""
    target: str = ""
    measurement: str = ""
    owner: str = ""


class PrdDataRequirement(StrictStageModel):
    field_name: str = ""
    source: str = ""
    purpose: str = ""
    freshness: str = ""
    quality_rule: str = ""


class PrdEventLog(StrictStageModel):
    event_name: str = ""
    trigger: str = ""
    properties: List[str] = Field(default_factory=list)
    purpose: str = ""


class PrdImplementationSlice(StrictStageModel):
    name: str = ""
    scope: List[str] = Field(default_factory=list)
    owner_hint: str = ""
    acceptance_criteria: List[str] = Field(default_factory=list)


class PrdDecisionAgendaItem(StrictStageModel):
    topic: str = ""
    decision_needed: str = ""
    owner: str = ""
    options: List[str] = Field(default_factory=list)


class PrdOpenQuestion(StrictStageModel):
    question: str = ""
    owner: str = ""
    needed_by: str = ""


class PrdPacket(StrictStageModel):
    stage_goal: str = ""
    one_page_summary: str = ""
    problem: PrdProblem = Field(default_factory=PrdProblem)
    personas: List[PrdPersona] = Field(default_factory=list)
    scope: PrdScope = Field(default_factory=PrdScope)
    screens: List[PrdScreenSpec] = Field(default_factory=list)
    policies: List[PrdPolicyRule] = Field(default_factory=list)
    metrics: List[PrdMetric] = Field(default_factory=list)
    data_requirements: List[PrdDataRequirement] = Field(default_factory=list)
    event_logs: List[PrdEventLog] = Field(default_factory=list)
    implementation_slices: List[PrdImplementationSlice] = Field(default_factory=list)
    decision_agenda: List[PrdDecisionAgendaItem] = Field(default_factory=list)
    open_questions: List[PrdOpenQuestion] = Field(default_factory=list)
    developer_handoff: List[str] = Field(default_factory=list)
    evidence_links: List[Citation] = Field(default_factory=list)


class PrdQualityReport(BaseModel):
    status: Literal["ready", "needs_review"] = "needs_review"
    score: int = 0
    findings: List[str] = Field(default_factory=list)
    repair_attempted: bool = False


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


class RunStageRequest(BaseModel):
    session_id: str
    user_input: str = ""
    context: Dict[str, Any] = Field(default_factory=dict)


class ApproveStageRequest(BaseModel):
    session_id: str
    stage_id: Optional[str] = None


class StageOutputBundle(BaseModel):
    summary: str
    planner_view: Dict[str, Any] = Field(default_factory=dict)
    engineer_view: Dict[str, Any] = Field(default_factory=dict)
    prd_packet: PrdPacket = Field(default_factory=PrdPacket)
    prd_quality: PrdQualityReport = Field(default_factory=PrdQualityReport)
    decision_points: List[DecisionItem] = Field(default_factory=list)
    required_user_input: List[str] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    risks: List[RiskItem] = Field(default_factory=list)
    rollback_targets: List[str] = Field(default_factory=list)


class StageResponse(BaseModel):
    session_id: str
    stage_id: str
    status: StageRunStatus
    output: StageOutputBundle
