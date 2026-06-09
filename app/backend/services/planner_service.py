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
            f"{label} 아이디어를 기술기획서로 옮기려면 해결할 사용자 문제, "
            "성공 KPI, MVP 경계를 먼저 합의해야 합니다."
        )
        if user_input:
            problem_summary = f"{problem_summary} 기획자 메모: {user_input}"
        summary = "아이디어를 문제 정의와 KPI 초안으로 구조화했습니다."

        return StageOutputBundle(
            summary=summary,
            planner_view={
                "problem_summary": problem_summary,
                "target_users": users,
                "kpi_candidates": kpis,
                "scope_candidates": [
                    "기획자가 설명할 사용자 문제",
                    "회의에서 결정할 MVP 경계",
                    "개발팀과 공유할 결정 로그",
                ],
            },
            engineer_view={
                "core_data": core_data,
                "data_readiness_question": (
                    "이 기획을 검토하는 데 필요한 데이터가 실제로 존재하고 연결 가능한가?"
                ),
                "initial_service_boundary": "기획자 승인형 의사결정 보조부터 시작",
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
                    item="자동화보다 기획자가 설명하고 승인할 수 있는 MVP 범위를 먼저 확정합니다.",
                    status="proposed",
                    rationale=(
                        "비개발 기획자가 개발팀과 논의할 수 있는 최소 단위로 "
                        "범위를 좁힙니다."
                    ),
                )
            ],
            required_user_input=[
                "이 아이디어의 1차 사용자를 확정해야 합니다.",
                "가장 먼저 검증할 핵심 KPI를 하나 골라야 합니다.",
            ],
            citations=citations,
            risks=[
                RiskItem(
                    category="data",
                    severity="medium",
                    description=(
                        "필요 데이터의 존재 여부가 불명확하면 기획서의 "
                        "실현 가능성이 낮아집니다."
                    ),
                    mitigation=(
                        "현재 확보된 데이터와 추가 확인이 필요한 데이터를 "
                        "분리해 표시합니다."
                    ),
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
            "핵심 사용자 문제를 보여주는 검토 화면",
            "추천 또는 경고 사유 설명",
            "담당자 승인/보류 액션",
            "결정 로그와 KPI 추적",
        ]
        summary = "아이디어를 MVP 범위와 구현 검토 단위로 좁혔습니다."
        return StageOutputBundle(
            summary=summary,
            planner_view={
                "feature_structure": {
                    "input": "기획자 메모, 핵심 KPI, 사용 가능한 데이터",
                    "decision": "MVP에 포함할 기능과 보류할 기능을 구분",
                    "output": "기획자가 승인한 범위와 결정 로그",
                },
                "mvp_in_scope": mvp_in_scope,
                "mvp_out_of_scope": [
                    "처음부터 완전 자동화",
                    "전사 확장용 고도화",
                    "검증 전 고객 노출 기능",
                ],
                "open_questions": [
                    "첫 파일럿 사용자는 누구인가?",
                    "성공 여부를 어떤 KPI로 판단할 것인가?",
                ],
            },
            engineer_view={
                "service_blocks": [
                    "아이디어 입력 정리",
                    "KPI와 범위 구조화",
                    "검토 화면 또는 정책 초안",
                    "승인 이벤트 저장",
                ],
                "primary_users": users,
                "mvp_scope": mvp_in_scope,
                "demo_note": user_input or "Use the selected planning brief.",
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
                    item="첫 MVP는 담당자가 검토하고 승인할 수 있는 보조 흐름으로 제한합니다.",
                    status="proposed",
                    rationale=(
                        "검증 전 자동화 범위를 키우면 데이터, 운영, 규제 "
                        "리스크를 설명하기 어렵습니다."
                    ),
                )
            ],
            required_user_input=["파일럿 사용자와 핵심 KPI를 선택해야 합니다."],
            citations=citations,
            risks=[
                RiskItem(
                    category="operational",
                    severity="medium",
                    description=(
                        "처음부터 기능 범위를 넓히면 기획자가 설명해야 할 "
                        "운영 변화가 과도해질 수 있습니다."
                    ),
                    mitigation=(
                        "회의에서 결정할 MVP 범위와 이후 고도화 범위를 명확히 분리합니다."
                    ),
                )
            ],
            rollback_targets=list(stage_def.rollback_targets if stage_def else []),
        )
