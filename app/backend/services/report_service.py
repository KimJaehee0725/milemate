"""Final report templates for the mock MVP."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.backend.core.config_loader import get_scenario_definition, get_stage_definition
from app.backend.schemas.common import Citation, DecisionItem, RiskItem
from app.backend.schemas.report import EngineerReport, FinalReportBundle, PlannerReport
from app.backend.schemas.stage import StageOutputBundle


class ReportService:
    """Build deterministic planner and engineer reports."""

    def build_reports(
        self,
        scenario: str,
        approved_state: Dict[str, Any],
        citations: Optional[List[dict | Citation]] = None,
        risks: Optional[List[dict | RiskItem]] = None,
    ) -> Dict[str, Any]:
        scenario_def = get_scenario_definition(scenario)
        label = scenario_def.label if scenario_def else scenario
        target_users = scenario_def.primary_users if scenario_def else []
        kpis = scenario_def.primary_kpis if scenario_def else []
        core_data = scenario_def.core_data if scenario_def else []

        problem_summary = approved_state.get(
            "problem_summary",
            f"{label} needs an operator-facing MVP with measurable dispatch outcomes.",
        )
        mvp_scope = approved_state.get(
            "mvp_scope",
            ["risk order queue", "dispatcher recommendation view", "override logging"],
        )

        planner_report = PlannerReport(
            problem_redefinition=problem_summary,
            target_users=target_users,
            prioritized_kpis=kpis,
            mvp_scope=mvp_scope,
            expected_value=[
                "reduce manual triage during peak periods",
                "make delay risk visible before SLA breach",
                "preserve dispatcher control through approval and override flow",
            ],
        )
        engineer_report = EngineerReport(
            required_data=core_data,
            required_tech_blocks=[
                "order and courier state ingestion",
                "delay-risk scoring rule/template",
                "recommendation API",
                "operator dashboard",
                "decision and override event log",
            ],
            constraints=[
                "MVP recommendations must be explainable to dispatchers.",
                "Location data should be minimized to dispatch-critical use.",
                "Pilot should avoid fully automated assignment changes.",
            ],
            implementation_order=[
                "load historical order/courier samples",
                "rank high-risk active orders",
                "show recommendation and reason codes",
                "collect dispatcher feedback",
            ],
            verification_plan=[
                "compare delay_rate before and after pilot",
                "track SLA compliance by zone and time window",
                "audit override reasons for false positives",
            ],
        )
        bundle = FinalReportBundle(
            planner_report=planner_report,
            engineer_report=engineer_report,
            decision_log=[
                DecisionItem(
                    item="Use a human-approved dispatch recommendation MVP.",
                    status="approved",
                    rationale="The mock workflow prioritizes feasibility and presentation clarity.",
                ),
                DecisionItem(
                    item="Defer full autonomous route optimization.",
                    status="deferred",
                    rationale="The first slice should validate data quality and operator trust.",
                ),
            ],
            citations=[
                item if isinstance(item, Citation) else Citation.model_validate(item)
                for item in (citations or [])
            ],
            risks=[
                item if isinstance(item, RiskItem) else RiskItem.model_validate(item)
                for item in (risks or [])
            ],
        )
        return bundle.model_dump()

    def build_stage_output(
        self,
        scenario: str,
        approved_state: Dict[str, Any],
        citations: Optional[List[Citation]] = None,
        risks: Optional[List[RiskItem]] = None,
    ) -> StageOutputBundle:
        stage_def = get_stage_definition("stage_4")
        report = self.build_reports(
            scenario=scenario,
            approved_state=approved_state,
            citations=citations or [],
            risks=risks or [],
        )
        return StageOutputBundle(
            summary="Final planner and engineer reports are ready for presentation.",
            planner_view=report["planner_report"],
            engineer_view=report["engineer_report"],
            decision_points=[
                DecisionItem.model_validate(item) for item in report["decision_log"]
            ],
            required_user_input=[],
            citations=[Citation.model_validate(item) for item in report["citations"]],
            risks=[RiskItem.model_validate(item) for item in report["risks"]],
            rollback_targets=list(stage_def.rollback_targets if stage_def else []),
        )
