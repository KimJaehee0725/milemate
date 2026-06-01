"""Deterministic planner templates for stages 1 and 2."""

from __future__ import annotations

from typing import List, Optional

from app.backend.core.config_loader import get_scenario_definition, get_stage_definition
from app.backend.schemas.common import Citation, DecisionItem, RiskItem
from app.backend.schemas.stage import StageOutputBundle
from app.backend.services.prd_packet_factory import build_demo_prd_packet, ready_prd_quality


class PlannerService:
    """Generate mock planner outputs from scenario config."""

    def build_stage_output(
        self,
        stage_id: str,
        scenario: str,
        user_input: str = "",
        citations: Optional[List[Citation]] = None,
    ) -> StageOutputBundle:
        if stage_id == "stage_1":
            return self._stage_1(
                scenario=scenario,
                user_input=user_input,
                citations=citations or [],
            )
        if stage_id == "stage_2":
            return self._stage_2(
                scenario=scenario,
                user_input=user_input,
                citations=citations or [],
            )
        raise ValueError(f"PlannerService does not handle {stage_id}")

    def _stage_1(
        self,
        scenario: str,
        user_input: str,
        citations: List[Citation],
    ) -> StageOutputBundle:
        scenario_def = get_scenario_definition(scenario)
        stage_def = get_stage_definition("stage_1")
        label = scenario_def.label if scenario_def else scenario
        users = scenario_def.primary_users if scenario_def else []
        kpis = scenario_def.primary_kpis if scenario_def else []
        core_data = scenario_def.core_data if scenario_def else []
        problem_summary = (
            f"{label} should reduce peak-time dispatch bottlenecks by surfacing "
            "which active orders need controller attention first."
        )
        if user_input:
            problem_summary = f"{problem_summary} Initial user note: {user_input}"
        summary = "Problem and KPI frame created for the dispatch planning slice."

        return StageOutputBundle(
            summary=summary,
            planner_view={
                "problem_summary": problem_summary,
                "target_users": users,
                "kpi_candidates": kpis,
                "scope_candidates": [
                    "risk order queue",
                    "priority recommendation",
                    "dispatcher approval log",
                ],
            },
            engineer_view={
                "core_data": core_data,
                "data_readiness_question": (
                    "Can order status and courier location be joined by time window?"
                ),
                "initial_service_boundary": "decision support only; no automatic reassignment",
            },
            prd_packet=build_demo_prd_packet(
                stage_id="stage_1",
                scenario=scenario,
                summary=summary,
                citations=citations,
                user_input=user_input,
            ),
            prd_quality=ready_prd_quality(),
            decision_points=[
                DecisionItem(
                    item="Optimize for dispatcher decision support before automation.",
                    status="proposed",
                    rationale="This creates a demoable MVP while limiting operational risk.",
                )
            ],
            required_user_input=[
                "Confirm the primary dispatch user for the demo.",
                "Confirm which KPI should be treated as the presentation headline.",
            ],
            citations=citations,
            risks=[
                RiskItem(
                    category="data",
                    severity="medium",
                    description="Courier location freshness may limit recommendation accuracy.",
                    mitigation="Start with high-delay zones and expose confidence notes.",
                )
            ],
            rollback_targets=list(stage_def.rollback_targets if stage_def else []),
        )

    def _stage_2(
        self,
        scenario: str,
        user_input: str,
        citations: List[Citation],
    ) -> StageOutputBundle:
        scenario_def = get_scenario_definition(scenario)
        stage_def = get_stage_definition("stage_2")
        users = scenario_def.primary_users if scenario_def else []
        mvp_in_scope = [
            "active order risk ranking",
            "recommended courier or route adjustment reason",
            "dispatcher approve/defer action",
            "decision log for later evaluation",
        ]
        summary = "Service structure narrowed to a human-approved recommendation MVP."
        return StageOutputBundle(
            summary=summary,
            planner_view={
                "feature_structure": {
                    "input": "live order and courier state",
                    "decision": "rank and explain dispatch intervention candidates",
                    "output": "dispatcher-approved recommendation log",
                },
                "mvp_in_scope": mvp_in_scope,
                "mvp_out_of_scope": [
                    "fully automated reassignment",
                    "global route optimization",
                    "customer-facing delay notification",
                ],
                "open_questions": [
                    "Which zone should be the pilot area?",
                    "What delay threshold triggers recommendation review?",
                ],
            },
            engineer_view={
                "service_blocks": [
                    "state ingestion",
                    "risk scoring",
                    "recommendation renderer",
                    "approval event store",
                ],
                "primary_users": users,
                "mvp_scope": mvp_in_scope,
                "demo_note": user_input or "Use dispatch.json default input.",
            },
            prd_packet=build_demo_prd_packet(
                stage_id="stage_2",
                scenario=scenario,
                summary=summary,
                citations=citations,
                user_input=user_input,
            ),
            prd_quality=ready_prd_quality(),
            decision_points=[
                DecisionItem(
                    item="Keep route changes as recommendations requiring dispatcher approval.",
                    status="proposed",
                    rationale=(
                        "This lets stage 3 verify feasibility without regulatory "
                        "or trust overreach."
                    ),
                )
            ],
            required_user_input=["Choose pilot zone and peak-hour window."],
            citations=citations,
            risks=[
                RiskItem(
                    category="operational",
                    severity="medium",
                    description=(
                        "Dispatcher overload can grow if too many recommendations are shown."
                    ),
                    mitigation=(
                        "Limit the queue to the highest-risk orders and support defer actions."
                    ),
                )
            ],
            rollback_targets=list(stage_def.rollback_targets if stage_def else []),
        )
