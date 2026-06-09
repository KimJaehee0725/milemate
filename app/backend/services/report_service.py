"""Final report templates for the mock MVP."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.backend.core.config_loader import get_scenario_definition, get_stage_definition
from app.backend.schemas.common import Citation, DecisionItem, RiskItem
from app.backend.schemas.report import EngineerReport, FinalReportBundle, PlannerReport
from app.backend.schemas.stage import StageOutputBundle
from app.backend.services.prd_packet_factory import build_demo_prd_packet, ready_prd_quality


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
            (
                f"{label} 아이디어는 기획자가 설명 가능한 MVP 범위와 "
                "측정 가능한 KPI로 정리되어야 합니다."
            ),
        )
        mvp_scope = approved_state.get(
            "mvp_scope",
            ["기획서 초안", "MVP 범위", "결정 로그"],
        )

        planner_report = PlannerReport(
            problem_redefinition=problem_summary,
            target_users=target_users,
            prioritized_kpis=kpis,
            mvp_scope=mvp_scope,
            expected_value=[
                "기획서 초안 작성 시간을 줄인다",
                "개발팀이 확인할 기술/데이터 리스크를 먼저 드러낸다",
                "기획자의 승인과 롤백 근거를 결정 로그로 남긴다",
            ],
        )
        engineer_report = EngineerReport(
            required_data=core_data,
            required_tech_blocks=[
                "idea intake and stage context",
                "KPI and MVP scope formatter",
                "risk verification boundary",
                "planner review UI",
                "decision and rollback event log",
            ],
            constraints=[
                "기획자가 읽을 수 있는 업무 언어와 개발팀 확인사항을 분리한다.",
                "데이터와 규제 리스크는 근거와 함께 표시한다.",
                "검증 전 완전 자동화 또는 실서비스 배포를 전제하지 않는다.",
            ],
            implementation_order=[
                "기획자 아이디어와 적용 예시를 입력한다",
                "문제 정의와 KPI 후보를 정리한다",
                "MVP 범위와 보류 기능을 나눈다",
                "승인/롤백 피드백을 수집한다",
            ],
            verification_plan=[
                "KPI별 현재 기준과 목표 기준이 모두 있는지 확인한다",
                "필수 데이터 출처와 품질 기준을 확인한다",
                "보류 조건과 결정 로그가 최종 보고서에 남는지 점검한다",
            ],
        )
        bundle = FinalReportBundle(
            planner_report=planner_report,
            engineer_report=engineer_report,
            prd_report=build_demo_prd_packet(
                stage_id="stage_4",
                scenario=scenario,
                summary=problem_summary,
                citations=[
                    item if isinstance(item, Citation) else Citation.model_validate(item)
                    for item in (citations or [])
                ],
            ),
            prd_quality=ready_prd_quality(),
            decision_log=[
                DecisionItem(
                    item="비개발 기획자가 승인할 수 있는 단계별 기획서 작성 흐름을 사용합니다.",
                    status="approved",
                    rationale=(
                        "이 단계에서는 실제 서비스 배포보다 기획서 구조화와 "
                        "의사결정 근거 정리가 핵심입니다."
                    ),
                ),
                DecisionItem(
                    item="검증 전 완전 자동화와 실서비스 배포 범위는 보류합니다.",
                    status="deferred",
                    rationale=(
                        "먼저 KPI, 데이터, 규제 리스크를 확인해야 개발 착수 "
                        "범위를 설명할 수 있습니다."
                    ),
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
        summary = "Final planner and engineer reports are ready for review."
        return StageOutputBundle(
            summary=summary,
            planner_view=report["planner_report"],
            engineer_view=report["engineer_report"],
            prd_packet=build_demo_prd_packet(
                stage_id="stage_4",
                scenario=scenario,
                summary=summary,
                citations=[Citation.model_validate(item) for item in report["citations"]],
            ),
            prd_quality=ready_prd_quality(),
            decision_points=[
                DecisionItem.model_validate(item) for item in report["decision_log"]
            ],
            required_user_input=[],
            citations=[Citation.model_validate(item) for item in report["citations"]],
            risks=[RiskItem.model_validate(item) for item in report["risks"]],
            rollback_targets=list(stage_def.rollback_targets if stage_def else []),
        )
