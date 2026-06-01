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
            f"{label}는 피크타임 운영자가 위험 주문을 먼저 확인하고 승인/보류할 수 "
            f"있는 추천형 MVP로 정리한다. {summary}{note}"
        ).strip(),
        problem=PrdProblem(
            customer_pain=(
                "고객은 지연 사유보다 언제 해결되는지와 안내가 믿을 만한지를 먼저 본다."
            ),
            business_impact=(
                "지연 주문이 늦게 발견되면 CS 문의, 쿠폰/보상 비용, 매장 클레임이 함께 늘어난다."
            ),
            current_workaround=(
                "운영자가 주문 목록과 배송원 상태를 수동으로 번갈아 확인하며 우선순위를 판단한다."
            ),
            success_criteria=[
                "피크타임 위험 주문을 운영자가 1분 안에 식별한다.",
                "추천 사유와 보류 사유가 모두 로그로 남는다.",
                "고객 안내 기준이 과장 없이 운영 정책과 일치한다.",
            ],
        ),
        personas=[
            PrdPersona(
                name="피크타임 배차 운영자",
                role=users[0] if users else "운영 담당자",
                needs=[
                    "위험 주문을 먼저 보고 싶다.",
                    "추천을 믿을 수 있는 사유와 기준을 확인하고 싶다.",
                ],
            ),
            PrdPersona(
                name="운영 리드",
                role="서비스 운영 의사결정자",
                needs=[
                    "지연률과 보상 비용을 같은 화면에서 보고 싶다.",
                    "운영자 재량과 자동화 경계를 명확히 두고 싶다.",
                ],
            ),
        ],
        scope=PrdScope(
            in_scope=[
                "위험 주문 목록",
                "추천 사유 노출",
                "운영자 승인/보류",
                "결정 로그와 KPI 집계",
            ],
            out_of_scope=[
                "완전 자동 재배차",
                "전 권역 최적화",
                "자동 보상 지급",
            ],
        ),
        screens=[
            PrdScreenSpec(
                name="피크타임 위험 주문 대시보드",
                purpose="운영자가 지연 가능성이 높은 주문을 우선순위대로 확인한다.",
                primary_user="피크타임 배차 운영자",
                entry_point="운영 콘솔 > 배차 관리 > 위험 주문",
                components=[
                    "권역/시간대 필터",
                    "위험 점수 컬럼",
                    "추천 사유",
                    "승인/보류 버튼",
                    "예상 영향 KPI",
                ],
                primary_actions=["추천 승인", "추천 보류", "주문 상세 확인"],
                empty_states=["현재 기준에 해당하는 위험 주문이 없음을 표시"],
                error_states=["위치 데이터가 지연되면 추천 신뢰도 낮음 배지를 표시"],
                acceptance_criteria=[
                    "위험 주문은 점수순으로 정렬된다.",
                    "승인/보류 시 사유와 담당자가 이벤트 로그에 저장된다.",
                    "데이터 freshness가 기준을 넘으면 운영자가 즉시 알 수 있다.",
                ],
            )
        ],
        policies=[
            PrdPolicyRule(
                name="추천 노출 기준",
                trigger="피크타임 권역에서 SLA 초과 가능성이 감지된 주문",
                rule="위험 점수 상위 주문만 운영자 검토 큐에 노출한다.",
                owner="서비스기획/운영",
                exception_handling="배송원 위치가 오래되면 추천 대신 확인 필요 상태로 표시한다.",
            )
        ],
        metrics=[
            PrdMetric(
                name=kpis[0] if kpis else "지연률",
                baseline="최근 2주 동일 권역/시간대 평균",
                target="파일럿 기간 10% 이상 개선",
                measurement="주문 완료 시각과 SLA 기준 시각 비교",
                owner="운영기획",
            ),
            PrdMetric(
                name=kpis[1] if len(kpis) > 1 else "보상/CS 비용",
                baseline="최근 2주 지연 관련 문의 및 쿠폰 지급 건수",
                target="파일럿 기간 5% 이상 감소",
                measurement="CS 태그, 쿠폰 발급 로그, 주문 권역을 조인",
                owner="서비스기획",
            ),
        ],
        data_requirements=[
            PrdDataRequirement(
                field_name=data_sources[0],
                source="주문 운영 DB",
                purpose="주문 상태와 SLA 잔여 시간을 계산",
                freshness="30초 이내",
                quality_rule="주문 ID와 상태 변경 시각은 필수",
            ),
            PrdDataRequirement(
                field_name=data_sources[1],
                source="배송원 위치/상태 스트림",
                purpose="배송원 공급과 이동 가능성을 판단",
                freshness="60초 이내",
                quality_rule="위치 수집 동의와 최신 수신 시각을 함께 저장",
            ),
            PrdDataRequirement(
                field_name=data_sources[2],
                source="권역/피크타임 운영 설정",
                purpose="추천 노출 권역과 시간대를 제한",
                freshness="일 단위",
                quality_rule="운영 설정 변경 이력을 보관",
            ),
        ],
        event_logs=[
            PrdEventLog(
                event_name="dispatch_recommendation_viewed",
                trigger="운영자가 위험 주문 상세를 열람",
                properties=["order_id", "zone_id", "risk_score", "reason_code", "operator_id"],
                purpose="추천 노출과 운영자 확인 여부 분석",
            ),
            PrdEventLog(
                event_name="dispatch_recommendation_decided",
                trigger="운영자가 추천을 승인하거나 보류",
                properties=["order_id", "decision", "decision_reason", "operator_id", "created_at"],
                purpose="승인율, 보류 사유, 모델 신뢰도 분석",
            ),
        ],
        implementation_slices=[
            PrdImplementationSlice(
                name="운영자 검토 큐 MVP",
                scope=["위험 주문 API", "추천 사유 렌더링", "승인/보류 이벤트 저장"],
                owner_hint="백엔드/프론트엔드/데이터",
                acceptance_criteria=[
                    "샘플 주문 데이터로 위험 주문 목록이 재현된다.",
                    "승인/보류 로그가 리포트 KPI 계산에 사용된다.",
                ],
            )
        ],
        decision_agenda=[
            PrdDecisionAgendaItem(
                topic="파일럿 권역과 피크타임 기준",
                decision_needed="강남/서초 등 첫 실험 권역과 시간대를 확정",
                owner="운영 리드",
                options=["강남/서초 저녁 피크", "주말 점심 피크", "클레임 상위 권역"],
            )
        ],
        open_questions=[
            PrdOpenQuestion(
                question="추천 신뢰도가 낮을 때 고객 안내를 어느 수준까지 허용할 것인가?",
                owner="서비스기획",
                needed_by="개발 착수 전",
            )
        ],
        developer_handoff=[
            "운영자 승인 없는 자동 재배차는 이번 범위에서 제외한다.",
            "모든 추천은 사유 코드와 데이터 최신성 배지를 함께 노출한다.",
            "승인/보류 이벤트는 파일럿 KPI 분석의 기준 로그로 사용한다.",
        ],
        evidence_links=list(citations or []),
    )


def _core_data(scenario_def: Any, evidence: dict[str, Any] | None) -> List[str]:
    evidence_sources = list((evidence or {}).get("data_sources") or [])
    configured = list(scenario_def.core_data if scenario_def else [])
    values = [*evidence_sources, *configured]
    defaults = ["order_status_event", "courier_location_event", "zone_peak_calendar"]
    merged: List[str] = []
    for value in [*values, *defaults]:
        if value and value not in merged:
            merged.append(str(value))
    return merged[:3]
