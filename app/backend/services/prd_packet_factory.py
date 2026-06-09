"""Small deterministic PRD packets for local demos and tests."""

from __future__ import annotations

from typing import Any, Iterable, List

from app.backend.core.config_loader import get_scenario_definition
from app.backend.schemas.common import Citation
from app.backend.schemas.stage import (
    PrdDataRequirement,
    PrdDecisionAgendaItem,
    PrdEventLog,
    PrdImplementationSlice,
    PrdMetric,
    PrdOpenQuestion,
    PrdPacket,
    PrdPersona,
    PrdPolicyRule,
    PrdProblem,
    PrdQualityReport,
    PrdScope,
    PrdScreenSpec,
)


def ready_prd_quality() -> PrdQualityReport:
    return PrdQualityReport(status="ready", score=100, findings=[], repair_attempted=False)


def build_demo_prd_packet(
    *,
    stage_id: str,
    scenario: str,
    summary: str,
    citations: Iterable[Citation] | None = None,
    user_input: str = "",
    evidence: dict[str, Any] | None = None,
) -> PrdPacket:
    scenario_def = get_scenario_definition(scenario)
    label = scenario_def.label if scenario_def else scenario
    users = list(scenario_def.primary_users if scenario_def else ["운영 담당자"])
    kpis = list(scenario_def.primary_kpis if scenario_def else ["지연률", "운영 처리시간"])
    data_sources = _core_data(scenario_def, evidence)
    stage_goal = {
        "stage_1": "서비스 문제와 성공 기준을 회의에서 합의할 수 있게 정리",
        "stage_2": "MVP 범위, 화면, 운영 정책을 개발 회의 수준으로 구체화",
        "stage_3": "데이터/운영 리스크와 보류 조건을 점검",
        "stage_4": "최종 추진안과 개발 착수 범위를 보고서 형태로 확정",
    }.get(stage_id, "서비스 기획 산출물 정리")
    note = f" 사용자 요청 반영: {user_input[:160]}" if user_input else ""

    return PrdPacket(
        stage_goal=stage_goal,
        one_page_summary=(
            f"{label} 아이디어를 기획자가 설명 가능한 기술기획서와 MVP 초안으로 "
            f"정리한다. {summary}{note}"
        ).strip(),
        problem=PrdProblem(
            customer_pain=(
                "사용자는 해결하려는 문제가 무엇인지, 어떤 경험이 달라지는지 명확히 알고 싶다."
            ),
            business_impact=(
                "문제와 KPI가 분리되어 있으면 개발 범위가 흔들리고 재작업 비용이 커진다."
            ),
            current_workaround=(
                "기획자가 자연어 메모와 회의 자료를 바탕으로 기능 요구사항을 수동 정리한다."
            ),
            success_criteria=[
                "핵심 사용자 문제와 KPI가 한 화면에서 설명된다.",
                "MVP 포함/제외 범위와 결정 사유가 로그로 남는다.",
                "기술, 데이터, 규제 리스크가 보류 조건과 함께 정리된다.",
            ],
        ),
        personas=[
            PrdPersona(
                name="비개발 기획자",
                role=users[0] if users else "서비스 기획자",
                needs=[
                    "아이디어를 개발팀과 논의할 수 있는 기획서로 바꾸고 싶다.",
                    "기술 제약과 데이터 필요조건을 쉽게 확인하고 싶다.",
                ],
            ),
            PrdPersona(
                name="개발 협업 담당자",
                role="엔지니어 또는 기술 리드",
                needs=[
                    "모호한 아이디어가 아니라 범위, API, 데이터, 제약이 정리된 문서를 받고 싶다.",
                    "왜 이 범위가 MVP인지 결정 근거를 확인하고 싶다.",
                ],
            ),
        ],
        scope=PrdScope(
            in_scope=[
                "아이디어 요약과 문제 정의",
                "KPI와 MVP 범위",
                "기술/데이터/규제 리스크 검토",
                "결정 로그와 KPI 집계",
            ],
            out_of_scope=[
                "검증 전 완전 자동화",
                "전사 확장용 고도화",
                "실서비스 배포 자동화",
            ],
        ),
        screens=[
            PrdScreenSpec(
                name="기획서 단계별 검토 화면",
                purpose="기획자가 아이디어, KPI, MVP 범위, 리스크를 단계별로 확인한다.",
                primary_user="비개발 기획자",
                entry_point="Milemate > 적용 예시 > 기획서 작성 시작",
                components=[
                    "아이디어 메모",
                    "문제 정의와 KPI 후보",
                    "MVP 포함/제외 범위",
                    "리스크와 보류 조건",
                    "승인/롤백 버튼",
                ],
                primary_actions=["단계 생성", "검토 후 승인", "이전 단계로 롤백"],
                empty_states=["아직 생성된 기획서 산출물이 없음을 표시"],
                error_states=["필수 데이터가 부족하면 검증 경고와 롤백 대상을 표시"],
                acceptance_criteria=[
                    "각 단계 산출물은 기획자가 읽을 수 있는 업무 언어로 표시된다.",
                    "승인/롤백 시 사유와 단계가 이벤트 로그에 저장된다.",
                    "데이터나 규제 리스크는 숨기지 않고 보류 조건으로 노출한다.",
                ],
            )
        ],
        policies=[
            PrdPolicyRule(
                name="MVP 범위 확정 기준",
                trigger="기획서 단계별 산출물을 승인하기 전",
                rule="기술, 데이터, 규제 리스크가 설명되지 않은 기능은 MVP에서 보류한다.",
                owner="서비스기획",
                exception_handling=(
                    "필수 데이터가 없으면 이전 단계로 돌아가 범위 또는 KPI를 "
                    "재조정한다."
                ),
            )
        ],
        metrics=[
            PrdMetric(
                name=kpis[0] if kpis else "지연률",
                baseline="현재 기획 검토 과정에서 측정 중인 기준",
                target="파일럿 기간 동안 개선 여부를 판단할 수 있는 수치 목표 확정",
                measurement="업무 로그, 사용자 행동, 비용 또는 품질 지표를 함께 검토",
                owner="운영기획",
            ),
            PrdMetric(
                name=kpis[1] if len(kpis) > 1 else "기획 검토 리드타임",
                baseline="기획서 초안 작성과 개발 검토에 걸리는 현재 시간",
                target="반복 회의와 재작업을 줄일 수 있는 수준으로 단축",
                measurement="초안 작성 시간, 수정 횟수, 승인 단계 로그를 조인",
                owner="서비스기획",
            ),
        ],
        data_requirements=[
            PrdDataRequirement(
                field_name=data_sources[0],
                source="현재 서비스 또는 운영 데이터",
                purpose="기획서에서 정의한 문제와 KPI의 현재 기준을 확인",
                freshness="검토 회의 전 최신 기준",
                quality_rule="지표 산식과 데이터 출처를 함께 기록",
            ),
            PrdDataRequirement(
                field_name=data_sources[1],
                source="사용자 행동 또는 업무 처리 로그",
                purpose="MVP가 실제 사용자 행동을 바꿀 수 있는지 판단",
                freshness="파일럿 분석에 사용할 수 있는 주기",
                quality_rule="개인정보와 수집 동의 조건을 함께 확인",
            ),
            PrdDataRequirement(
                field_name=data_sources[2],
                source="정책, 규제, 운영 제약 문서",
                purpose="기능 범위와 고객 안내 문구의 보류 조건을 판단",
                freshness="기획서 승인 전 재확인",
                quality_rule="근거 링크와 검토 책임자를 함께 남김",
            ),
        ],
        event_logs=[
            PrdEventLog(
                event_name="planning_stage_generated",
                trigger="기획자가 단계별 산출물을 생성",
                properties=["session_id", "stage_id", "scenario_id", "created_at"],
                purpose="아이디어가 어떤 단계에서 어떤 산출물로 바뀌었는지 추적",
            ),
            PrdEventLog(
                event_name="planning_stage_decided",
                trigger="기획자가 산출물을 승인하거나 롤백",
                properties=["session_id", "stage_id", "decision", "reason", "created_at"],
                purpose="결정 근거, 보류 사유, 재작업 지점을 분석",
            ),
        ],
        implementation_slices=[
            PrdImplementationSlice(
                name="기획서 검토 흐름 MVP",
                scope=["아이디어 입력", "단계별 산출물 표시", "승인/롤백 이벤트 저장"],
                owner_hint="기획/백엔드/프론트엔드",
                acceptance_criteria=[
                    "샘플 아이디어로 문제 정의, MVP 범위, 리스크 검토가 재현된다.",
                    "승인/롤백 로그가 최종 보고서의 결정 이력에 사용된다.",
                ],
            )
        ],
        decision_agenda=[
            PrdDecisionAgendaItem(
                topic="첫 MVP 범위와 성공 KPI",
                decision_needed="파일럿에서 검증할 핵심 사용자 문제와 KPI를 확정",
                owner="서비스 기획자",
                options=["문제 정의 우선", "MVP 범위 우선", "리스크 검증 우선"],
            )
        ],
        open_questions=[
            PrdOpenQuestion(
                question="기술/데이터 리스크가 남아 있을 때 어떤 기능을 MVP에서 제외할 것인가?",
                owner="서비스기획",
                needed_by="개발 착수 전",
            )
        ],
        developer_handoff=[
            "비개발 기획자가 읽을 수 있는 요약과 개발팀 확인사항을 같은 산출물에 분리해 제공한다.",
            "데이터 출처, 규제 리스크, 보류 조건은 승인 전에 반드시 표시한다.",
            "승인/롤백 이벤트는 최종 보고서의 Decision Log 기준으로 사용한다.",
        ],
        evidence_links=list(citations or []),
    )


def _core_data(scenario_def: Any, evidence: dict[str, Any] | None) -> List[str]:
    evidence_sources = list((evidence or {}).get("data_sources") or [])
    configured = list(scenario_def.core_data if scenario_def else [])
    values = [*evidence_sources, *configured]
    defaults = ["baseline_metric", "user_or_operation_log", "policy_constraint"]
    merged: List[str] = []
    for value in [*values, *defaults]:
        if value and value not in merged:
            merged.append(str(value))
    return merged[:3]
