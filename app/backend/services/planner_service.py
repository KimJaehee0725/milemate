"""Deterministic planner templates for stages 1 and 2."""

from __future__ import annotations

from typing import List, Optional

from app.backend.core.config_loader import get_scenario_definition, get_stage_definition
from app.backend.schemas.common import Citation, DecisionItem, RiskItem
from app.backend.schemas.stage import StageOutputBundle
from app.backend.services.prd_packet_factory import build_demo_prd_packet, ready_prd_quality
from app.backend.services.scenario_profiles import get_scenario_profile


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
        profile = get_scenario_profile(scenario)
        users = scenario_def.primary_users if scenario_def else []
        kpis = scenario_def.primary_kpis if scenario_def else []
        core_data = scenario_def.core_data if scenario_def else []
        problem_summary = profile["stage1_problem_summary"]
        if user_input:
            problem_summary = f"{problem_summary} 사용자 메모: {user_input}"
        summary = "문제와 KPI 프레임을 정리했습니다."

        return StageOutputBundle(
            summary=summary,
            planner_view={
                "problem_summary": problem_summary,
                "target_users": users,
                "kpi_candidates": kpis,
                "scope_candidates": list(profile["stage1_scope_candidates"]),
            },
            engineer_view={
                "core_data": core_data,
                "data_readiness_question": profile["stage1_engineer"]["data_readiness_question"],
                "initial_service_boundary": profile["stage1_engineer"]["initial_service_boundary"],
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
                    item="자동화 이전에 운영자 의사결정 지원부터 최적화한다.",
                    status="proposed",
                    rationale="검증 가능한 MVP를 만들면서 운영 리스크를 제한할 수 있다.",
                )
            ],
            required_user_input=[
                "주요 사용자를 확정해주세요.",
                "핵심 지표로 삼을 KPI를 확정해주세요.",
            ],
            citations=citations,
            risks=[
                RiskItem(
                    category="data",
                    severity="medium",
                    description="핵심 데이터의 최신성이 추천 정확도를 제한할 수 있다.",
                    mitigation="위험이 높은 구간부터 시작하고 신뢰도 메모를 함께 노출한다.",
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
        profile = get_scenario_profile(scenario)
        users = scenario_def.primary_users if scenario_def else []
        mvp_in_scope = list(profile["stage2_in_scope"])
        summary = "서비스 구조를 운영자 승인 기반 추천형 MVP로 좁혔습니다."
        return StageOutputBundle(
            summary=summary,
            planner_view={
                "feature_structure": dict(profile["stage2_feature_structure"]),
                "mvp_in_scope": mvp_in_scope,
                "mvp_out_of_scope": list(profile["stage2_out_scope"]),
                "open_questions": list(profile["stage2_open_questions"]),
            },
            engineer_view={
                "service_blocks": list(profile["stage2_service_blocks"]),
                "primary_users": users,
                "mvp_scope": mvp_in_scope,
                "demo_note": user_input or "기본 데모 입력을 사용합니다.",
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
                    item="개입 액션은 운영자 승인이 필요한 추천 형태로 유지한다.",
                    status="proposed",
                    rationale=(
                        "이렇게 하면 3단계에서 규제나 신뢰 과잉 없이 실현 가능성을 검증할 수 있다."
                    ),
                )
            ],
            required_user_input=["파일럿 대상 범위와 피크 시간대를 선택해주세요."],
            citations=citations,
            risks=[
                RiskItem(
                    category="operational",
                    severity="medium",
                    description=(
                        "추천을 너무 많이 노출하면 운영자 과부하가 커질 수 있다."
                    ),
                    mitigation=(
                        "검토 큐를 위험이 가장 높은 항목으로 제한하고 보류 액션을 지원한다."
                    ),
                )
            ],
            rollback_targets=list(stage_def.rollback_targets if stage_def else []),
        )
