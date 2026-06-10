"""Per-scenario Korean copy profiles for deterministic demo generation.

The local/demo runtime routes stage output through PlannerService,
VerifierService, ReportService, and build_demo_prd_packet. Without scenario
profiles those services emit identical dispatch-flavored text regardless of the
selected scenario. This module centralizes scenario-specific copy so each
service can branch on a single source of truth instead of scattered if/else.

Each profile exposes the same key set (see PROFILE_KEYS) so callers can rely on
uniform structure. get_scenario_profile() falls back to dispatch_recommendation
for unknown scenarios.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Keys every scenario profile must provide. Used by tests to assert parity.
PROFILE_KEYS = {
    "one_page_focus",
    "problem",
    "personas",
    "scope_in",
    "scope_out",
    "screen",
    "policy",
    "metrics",
    "data_requirements",
    "event_prefix",
    "event_logs",
    "impl_slice",
    "decision_agenda",
    "open_question",
    "developer_handoff",
    "stage1_problem_summary",
    "stage1_scope_candidates",
    "stage1_engineer",
    "stage2_feature_structure",
    "stage2_in_scope",
    "stage2_out_scope",
    "stage2_open_questions",
    "stage2_service_blocks",
    "verify_guardrails",
    "verify_scope_keywords",
}


_DISPATCH: Dict[str, Any] = {
    "one_page_focus": (
        "피크타임 운영자가 위험 주문을 먼저 확인하고 승인/보류할 수 있는 추천형 MVP로 정리한다."
    ),
    "problem": {
        "customer_pain": "고객은 지연 사유보다 언제 해결되는지와 안내가 믿을 만한지를 먼저 본다.",
        "business_impact": (
            "지연 주문이 늦게 발견되면 CS 문의, 쿠폰/보상 비용, 매장 클레임이 함께 늘어난다."
        ),
        "current_workaround": (
            "운영자가 주문 목록과 배송원 상태를 수동으로 번갈아 확인하며 우선순위를 판단한다."
        ),
        "success_criteria": [
            "피크타임 위험 주문을 운영자가 1분 안에 식별한다.",
            "추천 사유와 보류 사유가 모두 로그로 남는다.",
            "고객 안내 기준이 과장 없이 운영 정책과 일치한다.",
        ],
    },
    "personas": [
        {
            "name": "피크타임 배차 운영자",
            "role": "operations_manager",
            "needs": [
                "위험 주문을 먼저 보고 싶다.",
                "추천을 믿을 수 있는 사유와 기준을 확인하고 싶다.",
            ],
        },
        {
            "name": "운영 리드",
            "role": "서비스 운영 의사결정자",
            "needs": [
                "지연률과 보상 비용을 같은 화면에서 보고 싶다.",
                "운영자 재량과 자동화 경계를 명확히 두고 싶다.",
            ],
        },
    ],
    "scope_in": [
        "위험 주문 목록",
        "추천 사유 노출",
        "운영자 승인/보류",
        "결정 로그와 KPI 집계",
    ],
    "scope_out": [
        "완전 자동 재배차",
        "전 권역 최적화",
        "자동 보상 지급",
    ],
    "screen": {
        "name": "피크타임 위험 주문 대시보드",
        "purpose": "운영자가 지연 가능성이 높은 주문을 우선순위대로 확인한다.",
        "primary_user": "피크타임 배차 운영자",
        "entry_point": "운영 콘솔 > 배차 관리 > 위험 주문",
        "components": [
            "권역/시간대 필터",
            "위험 점수 컬럼",
            "추천 사유",
            "승인/보류 버튼",
            "예상 영향 KPI",
        ],
        "primary_actions": ["추천 승인", "추천 보류", "주문 상세 확인"],
        "empty_states": ["현재 기준에 해당하는 위험 주문이 없음을 표시"],
        "error_states": ["위치 데이터가 지연되면 추천 신뢰도 낮음 배지를 표시"],
        "acceptance_criteria": [
            "위험 주문은 점수순으로 정렬된다.",
            "승인/보류 시 사유와 담당자가 이벤트 로그에 저장된다.",
            "데이터 freshness가 기준을 넘으면 운영자가 즉시 알 수 있다.",
        ],
    },
    "policy": {
        "name": "추천 노출 기준",
        "trigger": "피크타임 권역에서 SLA 초과 가능성이 감지된 주문",
        "rule": "위험 점수 상위 주문만 운영자 검토 큐에 노출한다.",
        "owner": "서비스기획/운영",
        "exception_handling": "배송원 위치가 오래되면 추천 대신 확인 필요 상태로 표시한다.",
    },
    "metrics": [
        {
            "name": "지연률",
            "baseline": "최근 2주 동일 권역/시간대 평균",
            "target": "파일럿 기간 10% 이상 개선",
            "measurement": "주문 완료 시각과 SLA 기준 시각 비교",
            "owner": "운영기획",
        },
        {
            "name": "보상/CS 비용",
            "baseline": "최근 2주 지연 관련 문의 및 쿠폰 지급 건수",
            "target": "파일럿 기간 5% 이상 감소",
            "measurement": "CS 태그, 쿠폰 발급 로그, 주문 권역을 조인",
            "owner": "서비스기획",
        },
    ],
    "data_requirements": [
        {
            "source": "주문 운영 DB",
            "purpose": "주문 상태와 SLA 잔여 시간을 계산",
            "freshness": "30초 이내",
            "quality_rule": "주문 ID와 상태 변경 시각은 필수",
        },
        {
            "source": "배송원 위치/상태 스트림",
            "purpose": "배송원 공급과 이동 가능성을 판단",
            "freshness": "60초 이내",
            "quality_rule": "위치 수집 동의와 최신 수신 시각을 함께 저장",
        },
        {
            "source": "권역/피크타임 운영 설정",
            "purpose": "추천 노출 권역과 시간대를 제한",
            "freshness": "일 단위",
            "quality_rule": "운영 설정 변경 이력을 보관",
        },
    ],
    "event_prefix": "dispatch",
    "event_logs": [
        {
            "event_name": "dispatch_recommendation_viewed",
            "trigger": "운영자가 위험 주문 상세를 열람",
            "properties": ["order_id", "zone_id", "risk_score", "reason_code", "operator_id"],
            "purpose": "추천 노출과 운영자 확인 여부 분석",
        },
        {
            "event_name": "dispatch_recommendation_decided",
            "trigger": "운영자가 추천을 승인하거나 보류",
            "properties": ["order_id", "decision", "decision_reason", "operator_id", "created_at"],
            "purpose": "승인율, 보류 사유, 모델 신뢰도 분석",
        },
    ],
    "impl_slice": {
        "name": "운영자 검토 큐 MVP",
        "scope": ["위험 주문 API", "추천 사유 렌더링", "승인/보류 이벤트 저장"],
        "owner_hint": "백엔드/프론트엔드/데이터",
        "acceptance_criteria": [
            "샘플 주문 데이터로 위험 주문 목록이 재현된다.",
            "승인/보류 로그가 리포트 KPI 계산에 사용된다.",
        ],
    },
    "decision_agenda": {
        "topic": "파일럿 권역과 피크타임 기준",
        "decision_needed": "강남/서초 등 첫 실험 권역과 시간대를 확정",
        "owner": "운영 리드",
        "options": ["강남/서초 저녁 피크", "주말 점심 피크", "클레임 상위 권역"],
    },
    "open_question": {
        "question": "추천 신뢰도가 낮을 때 고객 안내를 어느 수준까지 허용할 것인가?",
        "owner": "서비스기획",
        "needed_by": "개발 착수 전",
    },
    "developer_handoff": [
        "운영자 승인 없는 자동 재배차는 이번 범위에서 제외한다.",
        "모든 추천은 사유 코드와 데이터 최신성 배지를 함께 노출한다.",
        "승인/보류 이벤트는 파일럿 KPI 분석의 기준 로그로 사용한다.",
    ],
    "stage1_problem_summary": (
        "동적 배차 및 경로 재추천은 피크타임 배차 집중을 줄이기 위해, 운영자가 먼저 살펴야 할 "
        "위험 주문과 권역을 드러내는 것을 목표로 한다."
    ),
    "stage1_scope_candidates": [
        "위험 주문 큐",
        "우선순위 추천",
        "배차 운영자 승인 로그",
    ],
    "stage1_engineer": {
        "data_readiness_question": "주문 상태와 배송원 위치를 시간대 기준으로 조인할 수 있는가?",
        "initial_service_boundary": "의사결정 지원 전용 · 자동 재배차 없음",
    },
    "stage2_feature_structure": {
        "input": "실시간 주문/배송원 상태",
        "decision": "배차 개입 후보를 점수화하고 사유를 설명",
        "output": "운영자가 승인한 추천 로그",
    },
    "stage2_in_scope": [
        "활성 주문 위험 순위화",
        "추천 배송원/경로 조정 사유",
        "운영자 승인/보류 액션",
        "사후 평가용 결정 로그",
    ],
    "stage2_out_scope": [
        "완전 자동 재배차",
        "전 권역 경로 최적화",
        "고객 대상 지연 알림",
    ],
    "stage2_open_questions": [
        "어느 권역을 파일럿 지역으로 할 것인가?",
        "어떤 지연 임계치에서 추천 검토를 발동할 것인가?",
    ],
    "stage2_service_blocks": [
        "상태 수집",
        "위험 점수화",
        "추천 렌더러",
        "승인 이벤트 저장소",
    ],
    "verify_guardrails": [
        "규칙과 순위 추천부터 시작한다",
        "운영자의 재정의를 로그로 남긴다",
        "지연률과 업무 편차를 매일 모니터링한다",
    ],
    "verify_scope_keywords": ["auto_assign", "full_optimization"],
}


_ETA: Dict[str, Any] = {
    "one_page_focus": (
        "지연 가능성이 높은 주문을 먼저 감지해 운영자가 고객 안내 타이밍을 판단하는 "
        "알림형 MVP로 정리한다."
    ),
    "problem": {
        "customer_pain": (
            "고객은 도착 시간을 신뢰하고 기다리는데, 안내가 늦거나 자주 바뀌면 "
            "불안과 문의로 이어진다."
        ),
        "business_impact": (
            "지연 안내가 늦으면 CS 문의가 급증하고, 보상 요구와 브랜드 신뢰 하락으로 비용이 커진다."
        ),
        "current_workaround": (
            "운영자가 실시간 주문 화면을 수동으로 보며 지연이 심해진 뒤에야 고객에게 안내한다."
        ),
        "success_criteria": [
            "지연 위험 주문을 운영자가 SLA 초과 전에 식별한다.",
            "고객 안내 문구와 발송 타이밍이 정책과 일치한다.",
            "알림 발송 이력과 사유가 모두 로그로 남는다.",
        ],
    },
    "personas": [
        {
            "name": "고객 경험 운영자",
            "role": "customer_experience_manager",
            "needs": [
                "지연 위험이 높은 주문을 먼저 보고 싶다.",
                "고객에게 보낼 안내 문구와 타이밍을 확인하고 싶다.",
            ],
        },
        {
            "name": "운영팀 담당자",
            "role": "operations_team",
            "needs": [
                "하루에 처리 가능한 알림 업무량을 유지하고 싶다.",
                "과한 알림으로 고객 피로도가 커지지 않게 하고 싶다.",
            ],
        },
    ],
    "scope_in": [
        "지연 위험 주문 목록",
        "예상 지연 시간과 사유 노출",
        "고객 안내 문구/타이밍 확인",
        "알림 발송 로그와 KPI 집계",
    ],
    "scope_out": [
        "자동 보상 지급",
        "정교한 마케팅 캠페인",
        "완전 자동 알림 발송",
    ],
    "screen": {
        "name": "지연 위험 주문 알림 콘솔",
        "purpose": "운영자가 지연 가능성이 높은 주문을 보고 고객 안내 타이밍을 판단한다.",
        "primary_user": "고객 경험 운영자",
        "entry_point": "운영 콘솔 > 고객 안내 > 지연 위험 주문",
        "components": [
            "예상 지연 시간 컬럼",
            "지연 사유 태그",
            "고객 안내 문구 미리보기",
            "알림 발송/보류 버튼",
            "알림 발송 이력",
        ],
        "primary_actions": ["안내 발송", "안내 보류", "주문 상세 확인"],
        "empty_states": ["현재 지연 위험이 높은 주문이 없음을 표시"],
        "error_states": ["위치/이동 데이터가 지연되면 예측 신뢰도 낮음 배지를 표시"],
        "acceptance_criteria": [
            "지연 위험 주문은 예상 초과 시간순으로 정렬된다.",
            "안내 발송 시 문구와 타이밍이 이벤트 로그에 저장된다.",
            "데이터 지연 시 운영자가 신뢰도 낮음을 즉시 인지한다.",
        ],
    },
    "policy": {
        "name": "고객 안내 발송 기준",
        "trigger": "예상 도착 시간이 약속 시간을 초과할 가능성이 감지된 주문",
        "rule": "지연 위험 상위 주문만 안내 검토 큐에 노출하고, 동일 주문 재알림 간격을 제한한다.",
        "owner": "고객경험/운영",
        "exception_handling": "예측 신뢰도가 낮으면 자동 안내 대신 운영자 확인 단계를 둔다.",
    },
    "metrics": [
        {
            "name": "ETA 정확도",
            "baseline": "최근 2주 ETA 오차 분포",
            "target": "오차 ±10분 이내 비율 파일럿 기간 15%p 개선",
            "measurement": "예측 ETA와 실제 도착 시각 차이 집계",
            "owner": "데이터/운영기획",
        },
        {
            "name": "지연 관련 CS 문의",
            "baseline": "최근 2주 지연 관련 문의 건수",
            "target": "파일럿 기간 10% 이상 감소",
            "measurement": "CS 태그와 알림 발송 로그를 주문 기준으로 조인",
            "owner": "고객경험",
        },
    ],
    "data_requirements": [
        {
            "source": "실시간 위치 스트림",
            "purpose": "현재 위치 기반으로 도착 예상 시간을 계산",
            "freshness": "30초 이내",
            "quality_rule": "위치 수집 동의와 최신 수신 시각을 함께 저장",
        },
        {
            "source": "이동 이력 저장소",
            "purpose": "구간별 소요 시간 패턴을 학습",
            "freshness": "일 단위",
            "quality_rule": "주문-구간 매핑 정합성을 보장",
        },
        {
            "source": "지연/안내 로그",
            "purpose": "과거 지연 패턴과 안내 효과를 분석",
            "freshness": "시간 단위",
            "quality_rule": "지연 사유 코드를 표준화",
        },
    ],
    "event_prefix": "eta",
    "event_logs": [
        {
            "event_name": "eta_delay_risk_viewed",
            "trigger": "운영자가 지연 위험 주문 상세를 열람",
            "properties": [
                "order_id",
                "predicted_delay",
                "reason_code",
                "confidence",
                "operator_id",
            ],
            "purpose": "지연 위험 노출과 운영자 확인 여부 분석",
        },
        {
            "event_name": "eta_notification_sent",
            "trigger": "운영자가 고객 안내를 발송하거나 보류",
            "properties": ["order_id", "action", "message_template", "sent_at", "operator_id"],
            "purpose": "안내 발송율, 보류 사유, 문의 감소 효과 분석",
        },
    ],
    "impl_slice": {
        "name": "지연 알림 검토 큐 MVP",
        "scope": ["지연 위험 주문 API", "안내 문구 렌더링", "발송/보류 이벤트 저장"],
        "owner_hint": "백엔드/프론트엔드/데이터",
        "acceptance_criteria": [
            "샘플 주문 데이터로 지연 위험 목록이 재현된다.",
            "발송/보류 로그가 문의 감소 KPI 계산에 사용된다.",
        ],
    },
    "decision_agenda": {
        "topic": "알림 발송 타이밍과 빈도 기준",
        "decision_needed": "선제 안내를 발송할 지연 임계치와 재알림 간격을 확정",
        "owner": "고객경험 리드",
        "options": ["SLA 초과 예상 10분 전", "초과 확정 시점", "위험도 상위 주문만"],
    },
    "open_question": {
        "question": "예측 신뢰도가 낮을 때 고객에게 어느 수준까지 선제 안내를 허용할 것인가?",
        "owner": "고객경험",
        "needed_by": "개발 착수 전",
    },
    "developer_handoff": [
        "운영자 확인 없는 완전 자동 안내는 이번 범위에서 제외한다.",
        "모든 안내는 예측 신뢰도와 사유 코드를 함께 노출한다.",
        "발송/보류 이벤트는 문의 감소 KPI 분석의 기준 로그로 사용한다.",
    ],
    "stage1_problem_summary": (
        "ETA 예측 및 지연 알림은 고객이 도착 시간을 신뢰할 수 있도록, 지연 위험이 높은 주문을 "
        "운영자가 SLA 초과 전에 식별하는 것을 목표로 한다."
    ),
    "stage1_scope_candidates": [
        "지연 위험 주문 큐",
        "예상 지연 시간/사유 노출",
        "고객 안내 발송 로그",
    ],
    "stage1_engineer": {
        "data_readiness_question": (
            "실시간 위치와 이동 이력을 주문 기준으로 시간대별 조인할 수 있는가?"
        ),
        "initial_service_boundary": "안내 의사결정 지원 전용 · 자동 발송 없음",
    },
    "stage2_feature_structure": {
        "input": "실시간 위치와 주문 진행 상태",
        "decision": "지연 위험 주문을 점수화하고 안내 타이밍을 제안",
        "output": "운영자가 확인한 고객 안내 발송 로그",
    },
    "stage2_in_scope": [
        "지연 위험 주문 순위화",
        "예상 지연 시간/사유 노출",
        "운영자 안내 발송/보류 액션",
        "문의 감소 평가용 발송 로그",
    ],
    "stage2_out_scope": [
        "완전 자동 알림 발송",
        "자동 보상 지급",
        "정교한 마케팅 캠페인",
    ],
    "stage2_open_questions": [
        "어떤 지연 임계치에서 선제 안내를 발동할 것인가?",
        "동일 주문 재알림 간격을 어떻게 제한할 것인가?",
    ],
    "stage2_service_blocks": [
        "위치/이동 데이터 수집",
        "지연 위험 점수화",
        "안내 문구 렌더러",
        "발송 이벤트 저장소",
    ],
    "verify_guardrails": [
        "예측 신뢰도가 낮으면 자동 안내 대신 운영자 확인을 둔다",
        "동일 주문 재알림 간격을 제한해 고객 피로도를 관리한다",
        "ETA 정확도와 문의 감소를 매일 모니터링한다",
    ],
    "verify_scope_keywords": ["auto_notification", "notification_automation"],
}


_FAILED: Dict[str, Any] = {
    "one_page_focus": (
        "실패 가능성이 높은 주문을 미리 감지해 운영팀이 사전 확인/개입할 수 있는 "
        "검토형 MVP로 정리한다."
    ),
    "problem": {
        "customer_pain": "고객은 배송 실패로 재시도와 재연락을 겪으며 불편을 느끼고 신뢰를 잃는다.",
        "business_impact": (
            "배송 실패는 재배송비, 상담 시간, 매장/기사 조율 비용을 함께 키운다."
        ),
        "current_workaround": (
            "운영팀이 실패가 발생한 뒤에야 사후 처리하며, 사전 예방 기준은 명확하지 않다."
        ),
        "success_criteria": [
            "실패 위험이 높은 주문을 운영팀이 출고 전에 식별한다.",
            "사전 확인/개입 액션과 사유가 모두 로그로 남는다.",
            "고객 연락 기준이 정책과 일치하고 과한 개입을 막는다.",
        ],
    },
    "personas": [
        {
            "name": "운영 품질 담당자",
            "role": "operations_quality_manager",
            "needs": [
                "실패 위험이 높은 주문을 먼저 보고 싶다.",
                "어떤 사전 확인이 효과적인지 사유와 함께 보고 싶다.",
            ],
        },
        {
            "name": "CS 운영팀 담당자",
            "role": "cs_operations_team",
            "needs": [
                "상담팀이 감당할 수 있는 개입 업무량을 유지하고 싶다.",
                "고객에게 불필요한 연락이 가지 않게 하고 싶다.",
            ],
        },
    ],
    "scope_in": [
        "실패 위험 주문 검토 큐",
        "위험 사유와 사전 확인 액션 노출",
        "운영팀 개입/보류 선택",
        "개입 결과 로그와 KPI 집계",
    ],
    "scope_out": [
        "자동 고객 연락",
        "실패 근본 원인 자동 예측",
        "자동 보상/환불 처리",
    ],
    "screen": {
        "name": "실패 위험 주문 검토 큐",
        "purpose": "운영팀이 실패 가능성이 높은 주문을 보고 사전 확인 액션을 선택한다.",
        "primary_user": "운영 품질 담당자",
        "entry_point": "운영 콘솔 > 배송 품질 > 실패 위험 주문",
        "components": [
            "실패 위험 점수 컬럼",
            "위험 사유 태그",
            "권장 사전 확인 액션",
            "개입/보류 버튼",
            "상담팀 처리 여력 표시",
        ],
        "primary_actions": ["사전 확인 진행", "개입 보류", "주문 상세 확인"],
        "empty_states": ["현재 실패 위험이 높은 주문이 없음을 표시"],
        "error_states": ["고객 응답 이력이 부족하면 예측 신뢰도 낮음 배지를 표시"],
        "acceptance_criteria": [
            "실패 위험 주문은 위험 점수순으로 정렬된다.",
            "개입/보류 시 사유와 담당자가 이벤트 로그에 저장된다.",
            "상담팀 처리 여력을 초과하면 노출량을 제한한다.",
        ],
    },
    "policy": {
        "name": "사전 개입 노출 기준",
        "trigger": "주문 특성과 고객 응답 이력에서 실패 가능성이 감지된 주문",
        "rule": (
            "실패 위험 상위 주문만 검토 큐에 노출하고, 상담팀 처리 여력 내로 개입량을 제한한다."
        ),
        "owner": "운영품질/CS",
        "exception_handling": (
            "고객 응답 이력이 민감하거나 부족하면 자동 연락 대신 운영팀 확인 단계를 둔다."
        ),
    },
    "metrics": [
        {
            "name": "배송 실패율",
            "baseline": "최근 2주 동일 권역 배송 실패율",
            "target": "파일럿 기간 실패율 15% 이상 개선",
            "measurement": "실패 처리 로그와 전체 배송 건수 비교",
            "owner": "운영품질",
        },
        {
            "name": "재배송 비용",
            "baseline": "최근 2주 재배송 건수와 처리 비용",
            "target": "파일럿 기간 재배송 비용 10% 이상 감소",
            "measurement": "재배송 로그, 상담 처리 시간, 주문 권역을 조인",
            "owner": "운영기획",
        },
    ],
    "data_requirements": [
        {
            "source": "배송 실패 로그",
            "purpose": "실패 패턴과 위험 신호를 식별",
            "freshness": "시간 단위",
            "quality_rule": "실패 사유 코드를 표준화",
        },
        {
            "source": "고객 응답 이력",
            "purpose": "연락 가능성과 부재 위험을 판단",
            "freshness": "일 단위",
            "quality_rule": "개인정보 최소 수집과 동의 범위를 준수",
        },
        {
            "source": "사전 개입 로그",
            "purpose": "개입 효과와 실패율 변화를 측정",
            "freshness": "시간 단위",
            "quality_rule": "개입 액션과 결과 매핑을 보관",
        },
    ],
    "event_prefix": "failed",
    "event_logs": [
        {
            "event_name": "failed_risk_order_viewed",
            "trigger": "운영팀이 실패 위험 주문 상세를 열람",
            "properties": ["order_id", "risk_score", "reason_code", "confidence", "operator_id"],
            "purpose": "실패 위험 노출과 운영팀 확인 여부 분석",
        },
        {
            "event_name": "failed_intervention_decided",
            "trigger": "운영팀이 사전 개입을 진행하거나 보류",
            "properties": [
                "order_id",
                "action",
                "intervention_reason",
                "operator_id",
                "created_at",
            ],
            "purpose": "개입율, 보류 사유, 실패율 개선 효과 분석",
        },
    ],
    "impl_slice": {
        "name": "실패 위험 검토 큐 MVP",
        "scope": ["실패 위험 주문 API", "위험 사유 렌더링", "개입/보류 이벤트 저장"],
        "owner_hint": "백엔드/프론트엔드/데이터",
        "acceptance_criteria": [
            "샘플 주문 데이터로 실패 위험 목록이 재현된다.",
            "개입/보류 로그가 실패율/재배송 KPI 계산에 사용된다.",
        ],
    },
    "decision_agenda": {
        "topic": "사전 개입 범위와 상담팀 업무량 기준",
        "decision_needed": "어떤 위험 수준부터 개입하고 일일 개입 상한을 어떻게 둘지 확정",
        "owner": "운영품질 리드",
        "options": ["위험 상위 10% 개입", "고객 응답 이력 기반 개입", "권역별 차등 개입"],
    },
    "open_question": {
        "question": "고객 응답 이력이 부족할 때 사전 연락을 어느 수준까지 허용할 것인가?",
        "owner": "운영품질",
        "needed_by": "개발 착수 전",
    },
    "developer_handoff": [
        "운영팀 확인 없는 자동 고객 연락은 이번 범위에서 제외한다.",
        "모든 위험 주문은 사유 코드와 예측 신뢰도를 함께 노출한다.",
        "개입/보류 이벤트는 실패율 개선 KPI 분석의 기준 로그로 사용한다.",
    ],
    "stage1_problem_summary": (
        "실패 배송 리스크 및 사전 개입은 재배송 비용과 고객 불편을 줄이기 위해, 실패 가능성이 "
        "높은 주문을 운영팀이 출고 전에 식별하는 것을 목표로 한다."
    ),
    "stage1_scope_candidates": [
        "실패 위험 주문 검토 큐",
        "위험 사유/권장 액션 노출",
        "운영팀 개입 결정 로그",
    ],
    "stage1_engineer": {
        "data_readiness_question": "주문 특성과 고객 응답 이력을 주문 기준으로 조인할 수 있는가?",
        "initial_service_boundary": "사전 확인 의사결정 지원 전용 · 자동 고객 연락 없음",
    },
    "stage2_feature_structure": {
        "input": "주문 특성과 고객 응답 이력",
        "decision": "실패 위험 주문을 점수화하고 사전 확인 액션을 제안",
        "output": "운영팀이 선택한 개입 결정 로그",
    },
    "stage2_in_scope": [
        "실패 위험 주문 순위화",
        "위험 사유/권장 액션 노출",
        "운영팀 개입/보류 액션",
        "실패율 평가용 개입 로그",
    ],
    "stage2_out_scope": [
        "자동 고객 연락",
        "실패 근본 원인 자동 예측",
        "자동 보상/환불 처리",
    ],
    "stage2_open_questions": [
        "어떤 위험 수준부터 사전 개입을 발동할 것인가?",
        "상담팀 처리 여력 내로 개입량을 어떻게 제한할 것인가?",
    ],
    "stage2_service_blocks": [
        "주문/응답 이력 수집",
        "실패 위험 점수화",
        "권장 액션 렌더러",
        "개입 이벤트 저장소",
    ],
    "verify_guardrails": [
        "고객 응답 이력이 부족하면 자동 연락 대신 운영팀 확인을 둔다",
        "상담팀 처리 여력 내로 일일 개입량을 제한한다",
        "실패율과 재배송 비용을 매일 모니터링한다",
    ],
    "verify_scope_keywords": ["auto_contact", "intervention_automation"],
}


_RIDER_ONBOARDING: Dict[str, Any] = {
    "one_page_focus": (
        "지금은 통째로 없는 흐름을, 막히는 신규 라이더를 운영자가 먼저 알아채 손 내미는 "
        "온보딩 케어 MVP로 새로 정리한다. 위험 감지는 자동, 먼저 연락/멘토 배정은 사람이 쥔다."
    ),
    "problem": {
        "customer_pain": (
            "신규 라이더는 첫날 어디서 픽업하는지 헤매고, 콜을 어떻게 잡는지 몰라 막히고, "
            "정산이 얼마 들어올지 깜깜해 마음이 식은 채 누구의 연락도 받지 못하고 조용히 앱을 떠난다."
        ),
        "business_impact": (
            "신규 1명당 평균 9만원의 모집 광고비가 첫 콜 완료 전 이탈로 회수되지 않고, "
            "첫 2주 잔존율이 40%에 머물러 공급이 늘 부족하다."
        ),
        "current_workaround": (
            "지금은 누가 그만두기 직전인지 알아챌 방법도, 먼저 손 내미는 절차도 통째로 없어, "
            "라이더가 완전히 떠난 뒤에야 잔존율 숫자로만 사후 확인한다."
        ),
        "success_criteria": [
            "첫 콜을 못 잡고 막힌 신규 라이더를 운영팀이 이탈 전에 식별한다.",
            "선제 연락·멘토 배정 액션과 사유가 모두 로그로 남아 효과를 측정할 수 있다.",
            "위험 판단 기준과 연락 멘트가 라이더에게 부담을 주지 않는 정책과 일치한다.",
        ],
    },
    "personas": [
        {
            "name": "라이더 성공 매니저",
            "role": "rider_success_manager",
            "needs": [
                "첫 2주에 막혀 이탈 직전인 신규 라이더를 한 화면에서 먼저 보고 싶다.",
                "누구에게 무슨 말로 먼저 연락해야 남는지 사유와 함께 알고 싶다.",
            ],
        },
        {
            "name": "공급 운영 리드",
            "role": "supply_operations_lead",
            "needs": [
                "모집 광고비 대비 잔존율과 연락 효과를 같은 화면에서 보고 싶다.",
                "자동 감지와 사람이 하는 연락의 경계를 명확히 두고 싶다.",
            ],
        },
    ],
    "scope_in": [
        "첫 2주 신규 라이더 이탈 위험 큐",
        "막힌 지점(첫 픽업·첫 콜·정산 이해)과 위험 사유 노출",
        "라이더 성공 매니저의 선제 연락·멘토 배정 결정",
        "연락 결과 로그와 잔존율·첫 콜 KPI 집계",
    ],
    "scope_out": [
        "라이더에게 자동으로 전화·메시지를 발송하는 완전 자동 연락",
        "이탈 근본 원인 자동 예측 및 자동 인센티브 지급",
        "정산 금액 자동 조정·선지급",
    ],
    "screen": {
        "name": "신규 라이더 온보딩 케어 큐",
        "purpose": (
            "라이더 성공 매니저가 첫 2주에 막혀 이탈 위험이 높은 신규 라이더를 먼저 보고 "
            "선제 연락·멘토 배정을 결정한다."
        ),
        "primary_user": "라이더 성공 매니저",
        "entry_point": "운영 콘솔 > 공급/라이더 > 신규 온보딩 케어",
        "components": [
            "이탈 위험 점수 컬럼",
            "막힌 단계 태그(첫 픽업/첫 콜/정산 이해)",
            "권장 연락 멘트·멘토 배정 제안",
            "연락 진행/보류 버튼",
            "가입 후 경과일·첫 콜 완료 여부 표시",
        ],
        "primary_actions": ["선제 연락 진행", "연락 보류", "라이더 온보딩 상세 확인"],
        "empty_states": ["현재 첫 2주 이탈 위험이 높은 신규 라이더가 없음을 표시"],
        "error_states": [
            "가입 직후라 활동 데이터가 부족하면 위험 점수 대신 신뢰도 낮음 배지를 표시"
        ],
        "acceptance_criteria": [
            "신규 라이더는 이탈 위험 점수순으로 정렬된다.",
            "연락 진행/보류 시 막힌 단계, 사유, 담당자가 이벤트 로그에 저장된다.",
            "활동 데이터가 부족한 신규 라이더는 위험 점수 대신 확인 필요 상태로 구분된다.",
        ],
    },
    "policy": {
        "name": "선제 연락 노출 기준",
        "trigger": (
            "가입 후 첫 2주 내 첫 콜 미완료 또는 첫 픽업·정산 이해 단계에서 막힘이 감지된 신규 라이더"
        ),
        "rule": (
            "이탈 위험 상위 신규 라이더만 케어 큐에 노출하고, 라이더 성공 매니저가 하루에 "
            "감당할 수 있는 연락량 내로 제한한다."
        ),
        "owner": "공급운영/라이더성공",
        "exception_handling": (
            "활동 데이터가 부족하거나 라이더가 연락 거부 의사를 밝힌 경우 자동 노출 대신 "
            "매니저 확인 단계를 둔다."
        ),
    },
    "metrics": [
        {
            "name": "첫 2주(14일) 잔존율",
            "baseline": "최근 8주 신규 코호트 14일 잔존율 40%",
            "target": "파일럿 기간 65% 이상으로 개선",
            "measurement": "신규 가입 코호트별 14일차 활동 라이더 수를 가입 수로 나눠 집계",
            "owner": "공급운영",
        },
        {
            "name": "첫 콜 완료까지 소요 시간",
            "baseline": "최근 8주 신규 라이더 첫 콜 완료 평균 5.2일",
            "target": "파일럿 기간 평균 2.5일 이내로 단축",
            "measurement": "가입 시각과 첫 콜 완료 시각의 차이를 코호트별로 집계",
            "owner": "라이더성공",
        },
    ],
    "data_requirements": [
        {
            "source": "라이더 온보딩 퍼널 로그",
            "purpose": "가입·교육 이수·첫 픽업·첫 콜 등 단계별 진행과 막힌 지점을 식별",
            "freshness": "시간 단위",
            "quality_rule": "라이더 ID와 각 단계 완료 시각은 필수, 단계 정의를 표준화",
        },
        {
            "source": "첫 콜 활동 스트림",
            "purpose": "첫 콜 수락·완료 여부와 시도 패턴으로 이탈 위험을 판단",
            "freshness": "30분 이내",
            "quality_rule": "콜 시도/수락/완료 상태와 시각의 정합성을 보장",
        },
        {
            "source": "정산 가시성·연락 동의 정보",
            "purpose": "예상 정산 안내 가능 여부와 연락 가능 채널·동의 범위를 확인",
            "freshness": "일 단위",
            "quality_rule": "개인정보 최소 수집과 연락 동의 범위·거부 이력을 함께 저장",
        },
    ],
    "event_prefix": "rider",
    "event_logs": [
        {
            "event_name": "rider_onboarding_risk_viewed",
            "trigger": "라이더 성공 매니저가 이탈 위험 신규 라이더 상세를 열람",
            "properties": [
                "rider_id",
                "days_since_signup",
                "stuck_stage",
                "risk_score",
                "confidence",
                "manager_id",
            ],
            "purpose": "위험 노출과 매니저 확인 여부, 막힌 단계 분포 분석",
        },
        {
            "event_name": "rider_onboarding_outreach_decided",
            "trigger": "라이더 성공 매니저가 선제 연락·멘토 배정을 진행하거나 보류",
            "properties": [
                "rider_id",
                "action",
                "outreach_reason",
                "channel",
                "manager_id",
                "created_at",
            ],
            "purpose": "연락 도달률, 보류 사유, 14일 잔존율·첫 콜 개선 효과 분석",
        },
    ],
    "impl_slice": {
        "name": "온보딩 케어 큐 MVP",
        "scope": [
            "신규 라이더 이탈 위험 API",
            "막힌 단계·위험 사유 렌더링",
            "연락 진행/보류 이벤트 저장",
        ],
        "owner_hint": "백엔드/프론트엔드/데이터",
        "acceptance_criteria": [
            "샘플 신규 라이더 데이터로 이탈 위험 큐가 재현된다.",
            "연락 진행/보류 로그가 14일 잔존율·첫 콜 KPI 계산에 사용된다.",
        ],
    },
    "decision_agenda": {
        "topic": "선제 연락 발동 기준과 매니저 일일 업무량",
        "decision_needed": (
            "어떤 막힘 신호(첫 콜 미완료 일수·교육 미이수 등)부터 연락하고 매니저 1인당 "
            "일일 연락 상한을 어떻게 둘지 확정"
        ),
        "owner": "공급운영 리드",
        "options": [
            "가입 후 3일 첫 콜 0건 시 연락",
            "첫 픽업·정산 이해 단계 막힘 우선",
            "위험 점수 상위 20%만 연락",
        ],
    },
    "open_question": {
        "question": (
            "가입 직후 활동 데이터가 거의 없는 신규 라이더에게는 어느 신호(교육 이수·앱 접속 등)로 "
            "위험을 판단하고 어느 수준까지 선제 연락을 허용할 것인가?"
        ),
        "owner": "라이더성공",
        "needed_by": "개발 착수 전",
    },
    "developer_handoff": [
        "라이더 성공 매니저 확인 없는 자동 전화·메시지 발송은 이번 범위에서 제외한다.",
        "모든 위험 신규 라이더는 막힌 단계와 위험 사유 코드, 예측 신뢰도를 함께 노출한다.",
        "연락 진행/보류 이벤트는 14일 잔존율·첫 콜 소요 시간 KPI 분석의 기준 로그로 사용한다.",
    ],
    "stage1_problem_summary": (
        "신규 라이더 온보딩·초기 이탈 방지는 어렵게 모집한 신규 라이더의 첫 2주 잔존율을 "
        "끌어올리기 위해, 첫 콜도 못 잡고 막혀 이탈 직전인 라이더를 운영팀이 떠나기 전에 "
        "식별하는 것을 목표로 한다. 지금은 누가 위태로운지 알아채는 흐름도, 먼저 손 내미는 "
        "절차도 통째로 없다."
    ),
    "stage1_scope_candidates": [
        "첫 2주 신규 라이더 이탈 위험 큐",
        "막힌 단계·위험 사유 노출",
        "라이더 성공 매니저 선제 연락 결정 로그",
    ],
    "stage1_engineer": {
        "data_readiness_question": (
            "가입·교육·첫 픽업·첫 콜 단계 로그를 라이더 ID 기준으로 시간순 조인해 "
            "가입 후 경과일을 계산할 수 있는가?"
        ),
        "initial_service_boundary": "이탈 위험 감지 및 연락 의사결정 지원 전용 · 자동 연락 없음",
    },
    "stage2_feature_structure": {
        "input": "신규 라이더의 온보딩 단계 진행과 첫 콜 활동 상태",
        "decision": "첫 2주 이탈 위험을 점수화하고 막힌 단계와 권장 연락 액션을 제안",
        "output": "라이더 성공 매니저가 선택한 선제 연락·멘토 배정 결정 로그",
    },
    "stage2_in_scope": [
        "신규 라이더 이탈 위험 순위화",
        "막힌 단계·위험 사유·권장 연락 액션 노출",
        "매니저 연락 진행/보류 액션",
        "잔존율·첫 콜 평가용 연락 결과 로그",
    ],
    "stage2_out_scope": [
        "라이더 대상 완전 자동 연락 발송",
        "이탈 근본 원인 자동 예측·자동 인센티브 지급",
        "정산 금액 자동 조정·선지급",
    ],
    "stage2_open_questions": [
        "어떤 막힘 신호와 경과일 기준에서 선제 연락을 발동할 것인가?",
        "매니저 일일 연락량 내로 위험 노출 건수를 어떻게 제한할 것인가?",
    ],
    "stage2_service_blocks": [
        "온보딩 단계·첫 콜 데이터 수집",
        "이탈 위험 점수화",
        "막힌 단계·권장 연락 렌더러",
        "연락 결정 이벤트 저장소",
    ],
    "verify_guardrails": [
        "활동 데이터가 부족하면 위험 점수 대신 매니저 확인 단계를 둔다",
        "매니저가 하루에 감당할 수 있는 연락량 내로 위험 노출을 제한한다",
        "14일 잔존율과 첫 콜 소요 시간을 코호트별로 매일 모니터링한다",
    ],
    "verify_scope_keywords": ["auto_outreach", "incentive_automation"],
}


_RETURN_PICKUP: Dict[str, Any] = {
    "one_page_focus": (
        "고객이 회수 시간대를 직접 예약하고 진행 상태를 추적하며, 부재 시 스스로 재예약하는 "
        "역배송 셀프서비스 MVP를 0에서 새로 정의한다."
    ),
    "problem": {
        "customer_pain": (
            "반품 신청 후 회수 일정이 전혀 안내되지 않아 고객이 박스를 싸둔 채 종일 대기하고, "
            "진행 상황을 확인할 화면이 없어 CS에 전화하는 것 외에 할 수 있는 일이 없다."
        ),
        "business_impact": (
            "회수 예약·추적 흐름이 통째로 없어 반품 회수 CS가 일 200건 누적되고, 부재로 인한 "
            "기사 헛걸음이 회수 비용을 키우며, 회수가 늦어진 일수만큼 재판매 가능 재고가 묶여 "
            "자금이 잠긴다."
        ),
        "current_workaround": (
            "정방향 배송만 있는 앱이라 회수 화면 자체가 없고, CS 상담사가 고객과 기사 사이에서 "
            "전화로 일정을 조율하며 기사 방문 시점은 정방향 동선에 임의로 끼워 넣는다."
        ),
        "success_criteria": [
            "고객이 반품 신청 직후 회수 시간대를 직접 선택하고 확정 안내를 받는다.",
            "회수 1차 방문 성공률이 베이스라인(58%) 대비 개선되고, 부재 시 재예약이 24시간 내 완료된다.",
            "회수 상태(예약→방문 예정→회수 완료→입고)가 고객 화면과 이벤트 로그에 동일하게 남는다.",
        ],
    },
    "personas": [
        {
            "name": "반품 고객",
            "role": "returning_customer",
            "needs": [
                "집에 있을 수 있는 시간대를 직접 골라 종일 헛기다림을 없애고 싶다.",
                "회수가 어디까지 진행됐는지, 환불은 언제쯤인지 한 화면에서 보고 싶다.",
            ],
        },
        {
            "name": "역물류 운영 담당자",
            "role": "reverse_logistics_operator",
            "needs": [
                "시간대별 회수 예약량이 권역 기사 여력을 넘지 않게 슬롯을 조절하고 싶다.",
                "부재·헛걸음 발생 건의 사유와 재예약 진행 상황을 한 화면에서 처리하고 싶다.",
            ],
        },
    ],
    "scope_in": [
        "고객 회수 시간대 선택·예약",
        "회수 상태 추적 타임라인(예약→방문 예정→회수 완료→입고)",
        "부재 시 고객 셀프 재예약",
        "운영자 시간대 여력(슬롯) 설정과 예약·시도 로그",
    ],
    "scope_out": [
        "회수 기사 자동 배차·동선 최적화",
        "환불·검수 자동 처리",
        "당일 즉시 회수 보장",
    ],
    "screen": {
        "name": "회수 예약·추적 화면",
        "purpose": "고객이 반품 회수 시간대를 직접 예약하고 진행 상태를 한 화면에서 추적한다.",
        "primary_user": "반품 고객",
        "entry_point": "앱 > 주문 내역 > 반품 신청 완료 > 회수 예약",
        "components": [
            "회수 가능 시간대 캘린더(권역 여력 기반 노출)",
            "선택 시간대 확정·변경 버튼",
            "회수 상태 타임라인(예약→방문 예정→회수 완료→입고)",
            "부재 시 재예약 안내 카드",
            "예상 환불 시점 안내",
        ],
        "primary_actions": ["회수 시간대 예약", "예약 변경/재예약", "회수 상태 확인"],
        "empty_states": [
            "예약 가능한 시간대가 없으면 다음 가능 일자와 빈자리 알림 신청을 안내"
        ],
        "error_states": [
            "시간대 여력 데이터 동기화가 실패하면 예약 버튼 대신 '시간대 확인 중' 상태와 CS 연결 경로를 노출"
        ],
        "acceptance_criteria": [
            "고객이 3탭 이내에 회수 시간대를 확정할 수 있다.",
            "예약·변경·재예약 이력이 사유 코드와 함께 이벤트 로그로 저장된다.",
            "회수 상태 변경은 5분 이내에 고객 화면 타임라인에 반영된다.",
        ],
    },
    "policy": {
        "name": "부재(헛걸음) 처리 기준",
        "trigger": (
            "기사가 예약 시간대에 방문했으나 고객 부재 또는 회수물 미준비로 회수 실패를 등록"
        ),
        "rule": (
            "실패 사유 코드를 기록한 뒤 고객에게 재예약 링크를 발송하고, 동일 반품 건의 "
            "재예약은 2회까지 셀프로 허용하며 이후는 운영자 확인 단계로 전환한다."
        ),
        "owner": "역물류 운영/CX기획",
        "exception_handling": (
            "고객이 48시간 내 재예약하지 않으면 자동 종결 대신 CS 상담사가 직접 연락 여부와 "
            "회수 지속 여부를 판단한다."
        ),
    },
    "metrics": [
        {
            "name": "회수 1차 방문 성공률",
            "baseline": "최근 4주 1차 방문 회수 성공률 58%",
            "target": "파일럿 기간 85% 이상",
            "measurement": "회수 시도 로그에서 1차 방문 성공 건수를 전체 1차 시도 건수로 나눠 권역별 집계",
            "owner": "역물류 운영",
        },
        {
            "name": "반품 회수 관련 CS 문의",
            "baseline": "최근 4주 일 평균 200건",
            "target": "파일럿 기간 30% 감소",
            "measurement": "CS 태그(반품 회수)와 반품 주문 ID를 조인해 예약 기능 노출 전후 일 단위 비교",
            "owner": "CX기획",
        },
    ],
    "data_requirements": [
        {
            "source": "반품/교환 신청 DB",
            "purpose": "회수 대상 주문과 회수지 주소, 상품·연락처 정보를 확보",
            "freshness": "1분 이내",
            "quality_rule": "반품 주문 ID·회수지 주소·연락처는 필수, 주소 변경 이력을 보관",
        },
        {
            "source": "회수 시간대 여력(슬롯) 설정",
            "purpose": "권역·시간대별 예약 가능 슬롯을 계산해 과예약을 방지",
            "freshness": "10분 이내",
            "quality_rule": "권역별 슬롯 상한과 변경 이력을 변경자와 함께 저장",
        },
        {
            "source": "회수 시도/완료 로그",
            "purpose": "방문·성공·실패(부재) 상태를 타임라인과 KPI에 반영",
            "freshness": "5분 이내",
            "quality_rule": "실패 사유 코드(부재/미준비/주소오류)를 표준화하고 시도 회차를 함께 기록",
        },
    ],
    "event_prefix": "return",
    "event_logs": [
        {
            "event_name": "return_pickup_slot_booked",
            "trigger": "고객이 회수 시간대를 예약하거나 변경·재예약",
            "properties": [
                "return_id",
                "slot_date",
                "slot_window",
                "booking_type",
                "zone_id",
                "customer_id",
            ],
            "purpose": "시간대 선호 분포, 예약 변경률, 재예약 전환율 분석",
        },
        {
            "event_name": "return_pickup_attempt_logged",
            "trigger": "기사가 방문 결과(회수 완료/부재/미준비)를 등록",
            "properties": [
                "return_id",
                "attempt_no",
                "result_code",
                "fail_reason",
                "rebook_link_sent",
                "courier_id",
            ],
            "purpose": "1차 방문 성공률, 부재 사유 구성, 헛걸음 비용 분석",
        },
    ],
    "impl_slice": {
        "name": "회수 예약·추적 MVP",
        "scope": [
            "회수 가능 시간대 조회/예약 API",
            "회수 상태 타임라인 화면",
            "부재 등록과 재예약 링크 발송",
            "예약·시도 이벤트 저장",
        ],
        "owner_hint": "백엔드/프론트엔드/데이터",
        "acceptance_criteria": [
            "샘플 반품 주문으로 예약→방문→부재→재예약→회수 완료 흐름이 재현된다.",
            "예약·시도 로그가 1차 성공률과 CS 문의 감소 KPI 계산에 사용된다.",
        ],
    },
    "decision_agenda": {
        "topic": "회수 시간대 단위와 예약 여력 기준",
        "decision_needed": "시간대 슬롯 폭과 권역별 일일 예약 슬롯 상한을 확정",
        "owner": "역물류 운영 리드",
        "options": [
            "2시간 단위 슬롯(고객 대기 짧지만 기사 여력 부담)",
            "4시간 단위 슬롯(균형안)",
            "오전/오후 반일 슬롯(여력 여유, 고객 대기 김)",
        ],
    },
    "open_question": {
        "question": "회수 기사를 정방향 배송 기사와 겸용으로 운영할지, 회수 전담 풀을 별도로 둘지?",
        "owner": "역물류 운영 리드",
        "needed_by": "파일럿 권역 확정 전",
    },
    "developer_handoff": [
        "시간대 추천·상태 가시화까지는 자동이지만, 기사 배정 확정과 고객 직접 연락은 기존 운영 절차(사람)가 수행한다.",
        "예약·변경·방문 결과는 모두 사유 코드와 시도 회차를 포함해 이벤트 로그로 남기고 KPI 분석의 기준으로 사용한다.",
        "정방향 배송 상태 모델과 분리된 역배송 상태 모델(예약→방문 예정→회수 완료→입고)을 새로 정의한다.",
    ],
    "stage1_problem_summary": (
        "반품·교환 회수 예약·추적은 현재 앱에 역배송 흐름이 통째로 존재하지 않아 고객 종일 "
        "대기, 기사 헛걸음, 환불 지연 문의가 누적되는 문제를 풀기 위해, 고객이 회수 시간대를 "
        "직접 예약하고 상태를 추적하는 흐름을 처음부터 새로 만드는 것을 목표로 한다."
    ),
    "stage1_scope_candidates": [
        "고객 회수 시간대 예약",
        "회수 상태 추적 타임라인",
        "부재 시 셀프 재예약",
    ],
    "stage1_engineer": {
        "data_readiness_question": (
            "반품 신청 데이터에 회수지 주소·연락처가 정확히 있고, 권역·시간대별 기사 여력을 "
            "예약 슬롯으로 계산할 수 있는가?"
        ),
        "initial_service_boundary": (
            "예약·추적·재예약 셀프서비스 전용 · 기사 자동 배차와 환불 자동 처리 없음"
        ),
    },
    "stage2_feature_structure": {
        "input": "반품 신청 정보와 권역·시간대별 회수 여력",
        "decision": "예약 가능한 시간대를 계산해 노출하고, 부재 시 재예약 경로를 제안",
        "output": "고객이 확정한 예약과 방문 결과가 쌓이는 회수 상태 로그",
    },
    "stage2_in_scope": [
        "회수 가능 시간대 계산·노출",
        "고객 예약·변경·재예약",
        "회수 상태 타임라인",
        "예약·시도 이벤트 로그",
    ],
    "stage2_out_scope": [
        "회수 기사 자동 배차·동선 최적화",
        "환불·검수 자동 처리",
        "당일 즉시 회수 보장",
    ],
    "stage2_open_questions": [
        "시간대 슬롯 폭을 2시간/4시간/반일 중 무엇으로 시작할 것인가?",
        "부재 2회 이후 건을 자동 종결할지 운영자 판단으로 넘길지?",
    ],
    "stage2_service_blocks": [
        "반품 신청 연동",
        "시간대 여력 계산",
        "예약·재예약 처리",
        "회수 상태 이벤트 저장소",
    ],
    "verify_guardrails": [
        "시간대 추천과 상태 가시화까지만 자동으로 하고, 기사 배정 확정과 고객 직접 연락은 운영자가 결정한다",
        "재예약 자동 안내는 링크 발송으로 한정하고 셀프 재예약 횟수(2회)를 제한해 고객 피로도와 헛걸음 반복을 막는다",
        "1차 방문 성공률과 헛걸음 건수를 매일 모니터링해 권역별 슬롯 상한을 조정한다",
    ],
    "verify_scope_keywords": ["auto_dispatch", "auto_refund"],
}


_CHECKOUT_FEE: Dict[str, Any] = {
    "one_page_focus": (
        "주문 전부터 '이 주소·이 조건이면 배송비·수수료가 왜 이 금액인지'를 분해해 미리 "
        "보여주는 사전 안내형 신규 기능으로 정리하되, 금액 계산·분해·표시는 자동, "
        "실제 청구 확정과 예외 보정은 사람이 쥔다."
    ),
    "problem": {
        "customer_pain": (
            "고객은 상품을 고를 때 본 가격으로 결제할 거라 기대하는데, 결제 마지막 화면에서 "
            "배송비·수수료가 갑자기 더해져 '왜 비싸졌는지' 납득하지 못한 채 장바구니를 떠난다."
        ),
        "business_impact": (
            "결제 직전 가격 점프로 장바구니 이탈이 발생해 매출 전환이 깨지고, '예상과 다르다'는 "
            "배송비 관련 CS 문의·환불 요구가 반복되며 상담 비용과 신뢰 하락이 함께 커진다."
        ),
        "current_workaround": (
            "지금은 주문 전 배송비를 설명하는 화면이 통째로 없어, 고객은 결제 단계에서야 합산 "
            "금액을 처음 보고 운영팀은 문의가 들어올 때마다 수기로 거리·시간대·할증을 사후 설명한다."
        ),
        "success_criteria": [
            "고객이 주문 전(상품/장바구니 단계)에 이 주소의 배송비·수수료 예상 범위와 사유를 확인할 수 있다.",
            "사전 안내에 표시한 예상 금액과 실제 결제 금액의 차이를 정해진 허용 범위 안으로 관리하고, 벗어난 케이스를 모두 로그로 남긴다.",
            "배송비 산정 사유(거리·시간대·할증 등)가 과장 없이 실제 요금 규칙과 일치한다.",
        ],
    },
    "personas": [
        {
            "name": "결제 전환 담당 기획자",
            "role": "commerce_checkout_planner",
            "needs": [
                "결제 직전 가격 점프로 인한 이탈 지점을 데이터로 보고 싶다.",
                "배송비·수수료를 어느 단계에서 어떻게 미리 보여줄지 안전한 범위를 잡고 싶다.",
            ],
        },
        {
            "name": "고객 CS 운영 담당자",
            "role": "cs_operations_lead",
            "needs": [
                "예상 금액과 실제 청구가 달라 들어오는 문의를 줄이고 싶다.",
                "고객에게 설명할 배송비 사유 문구가 실제 규칙과 어긋나지 않게 하고 싶다.",
            ],
        },
    ],
    "scope_in": [
        "주소·장바구니 기준 배송비·수수료 예상 금액 분해 계산",
        "주문 전 사전 안내 카드(예상 범위 + 산정 사유 문구) 노출",
        "예상가-실제가 차이 감지 및 불일치 케이스 로그·플래그",
        "이탈/문의 평가용 사전 안내 노출·확인 이벤트 집계",
    ],
    "scope_out": [
        "배송비·수수료 정책 자체의 자동 변경·할인 적용",
        "예상가와 실제가 차이에 대한 자동 환불·보상 지급",
        "개인화 프로모션·동적 가격 최적화",
    ],
    "screen": {
        "name": "결제 전 배송비·수수료 분해 안내 카드",
        "purpose": (
            "고객이 주문을 확정하기 전에 이 주소·조건의 배송비·수수료가 왜 이 금액인지 "
            "분해된 내역과 사유로 미리 이해하게 한다."
        ),
        "primary_user": "장바구니/결제 진입 고객",
        "entry_point": "상품 상세 또는 장바구니 > 주소 입력/확인 > 예상 배송비 안내",
        "components": [
            "상품가 + 배송비 + 수수료 합산 요약",
            "배송비 분해 항목(기본료·거리 할증·시간대 할증)",
            "산정 사유 문구(예: 도서산간/심야 등)",
            "예상 금액 범위와 '실제 결제 시 변동 가능' 안내 배지",
            "데이터 신뢰도/적용 기준일 표시",
        ],
        "primary_actions": ["배송비 상세 펼쳐보기", "주소 변경 후 다시 계산", "결제로 진행"],
        "empty_states": ["주소가 아직 입력되지 않아 예상 배송비를 계산할 수 없음을 안내"],
        "error_states": [
            "요금 규칙/거리 데이터가 지연되면 정확한 금액 대신 범위와 '결제 화면에서 확정' 안내를 표시"
        ],
        "acceptance_criteria": [
            "주소가 입력되면 합산 금액과 배송비 분해 항목이 함께 표시된다.",
            "사전 안내 노출·펼침·결제 진행이 이벤트 로그로 저장된다.",
            "요금 데이터가 기준 신뢰도를 넘지 못하면 단일 확정 금액 대신 예상 범위로 표기된다.",
        ],
    },
    "policy": {
        "name": "예상 금액 사전 노출 기준",
        "trigger": "주소·장바구니가 확정되어 배송비·수수료 예상 금액을 계산할 수 있게 된 시점",
        "rule": (
            "요금 규칙·거리 데이터 신뢰도가 기준 이상일 때만 단일 예상 금액을 표시하고, "
            "미만이면 예상 범위와 변동 가능 안내로만 노출한다. 실제 청구 확정은 결제 단계 "
            "계산 결과를 따른다."
        ),
        "owner": "커머스 결제기획/CS",
        "exception_handling": (
            "예상가와 실제가 차이가 허용 범위를 초과하면 자동 노출을 멈추고 운영자 확인 큐로 "
            "보내 사유 문구·요금 규칙을 점검한 뒤 재개한다."
        ),
    },
    "metrics": [
        {
            "name": "결제 단계 장바구니 이탈률",
            "baseline": "최근 4주 결제 진입 후 미완료 비율",
            "target": "파일럿 기간 25% 이상 감소",
            "measurement": "결제 진입 이벤트와 결제 완료 이벤트를 세션 기준으로 비교",
            "owner": "커머스 결제기획",
        },
        {
            "name": "배송비 관련 CS 문의",
            "baseline": "최근 4주 배송비·예상가 불일치 관련 문의 건수",
            "target": "파일럿 기간 35% 이상 감소",
            "measurement": "CS 태그(배송비/요금 불일치)와 사전 안내 노출 로그를 주문 기준으로 조인",
            "owner": "CS 운영",
        },
    ],
    "data_requirements": [
        {
            "source": "배송비·수수료 요금 규칙 테이블",
            "purpose": "기본료, 거리·시간대 할증, 도서산간 등 산정 규칙을 적용해 예상 금액과 분해 항목을 계산",
            "freshness": "일 단위(규칙 변경 즉시 반영)",
            "quality_rule": "요금 규칙 버전과 적용 기준일을 함께 보관하고 변경 이력을 남긴다",
        },
        {
            "source": "주소·거리 산정 데이터",
            "purpose": "배송 주소와 출발지 간 거리/권역을 계산해 거리 할증 근거를 만든다",
            "freshness": "주소 입력 시점 실시간",
            "quality_rule": "주소 정규화 실패·권역 미매핑 시 단일 금액 대신 범위로 처리한다",
        },
        {
            "source": "예상가-실제가 정산 로그",
            "purpose": "사전 안내 예상 금액과 결제 확정 금액의 차이를 측정해 불일치 케이스를 추적",
            "freshness": "결제 완료 시점 실시간",
            "quality_rule": "예상 금액·실제 금액·차이 사유 코드를 주문 ID에 매핑해 보관한다",
        },
    ],
    "event_prefix": "fee",
    "event_logs": [
        {
            "event_name": "fee_breakdown_previewed",
            "trigger": "고객이 주문 전 배송비·수수료 분해 안내 카드를 본 시점",
            "properties": [
                "session_id",
                "address_zone",
                "estimated_total",
                "estimated_shipping",
                "reason_codes",
                "confidence_level",
            ],
            "purpose": "사전 안내 노출이 이탈 지점과 결제 진행에 미치는 영향을 분석",
        },
        {
            "event_name": "fee_estimate_mismatch_logged",
            "trigger": "결제 확정 금액이 사전 안내 예상 금액과 허용 범위를 벗어나게 다른 경우",
            "properties": [
                "order_id",
                "estimated_total",
                "charged_total",
                "delta_amount",
                "mismatch_reason",
                "created_at",
            ],
            "purpose": "예상가-실제가 불일치율과 사유를 추적해 노출 기준·요금 규칙을 보정",
        },
    ],
    "impl_slice": {
        "name": "사전 배송비 분해 안내 카드 MVP",
        "scope": [
            "요금 규칙 기반 예상가 분해 계산 API",
            "주소 기준 배송비 안내 카드 렌더링",
            "예상가 노출·불일치 이벤트 저장",
        ],
        "owner_hint": "백엔드/프론트엔드/데이터",
        "acceptance_criteria": [
            "샘플 주소·장바구니로 예상 배송비 분해 카드가 재현된다.",
            "예상가-실제가 불일치 로그가 이탈률·CS 문의 KPI 계산에 사용된다.",
        ],
    },
    "decision_agenda": {
        "topic": "사전 안내 노출 단계와 예상가 허용 오차 기준",
        "decision_needed": (
            "사전 안내를 어느 단계(상품/장바구니/주소 입력)부터 띄우고, 예상가와 실제가 차이를 "
            "어디까지 '일치'로 볼지 허용 오차를 확정"
        ),
        "owner": "커머스 결제기획 리드",
        "options": ["장바구니 단계부터 노출", "주소 입력 직후 노출", "결제 직전 분해만 강화"],
    },
    "open_question": {
        "question": (
            "요금 데이터 신뢰도가 낮을 때 단일 예상 금액을 숨기고 범위만 보여주는 기준선을 "
            "어디에 둘 것인가?"
        ),
        "owner": "커머스 결제기획",
        "needed_by": "개발 착수 전",
    },
    "developer_handoff": [
        "배송비·수수료 정책 자체의 자동 변경·할인 적용은 이번 범위에서 제외한다(표시·계산만 자동, 정책 변경은 사람).",
        "모든 예상 금액은 산정 사유 코드와 요금 규칙 버전·신뢰도를 함께 노출한다.",
        "예상가-실제가 불일치 이벤트는 이탈률·CS 문의 감소 KPI 분석의 기준 로그로 사용한다.",
    ],
    "stage1_problem_summary": (
        "결제 전 배송비·수수료 투명 안내는, 지금은 주문 전에 배송비를 설명하는 화면이 통째로 "
        "없어 결제 마지막에야 금액이 더해지며 발생하는 장바구니 이탈과 예상가-실제가 불일치 "
        "문의를 줄이기 위해, 주소·조건 기준 배송비 산정 사유를 사전에 보여주는 신규 안내 "
        "기능을 만드는 것을 목표로 한다."
    ),
    "stage1_scope_candidates": [
        "주소 기준 배송비·수수료 예상 분해",
        "주문 전 사전 안내 카드와 사유 문구",
        "예상가-실제가 불일치 추적 로그",
    ],
    "stage1_engineer": {
        "data_readiness_question": (
            "배송비 요금 규칙과 주소·거리 데이터를 주문 시점 기준으로 결합해 결제 확정 계산과 "
            "동일한 로직으로 예상가를 산출할 수 있는가?"
        ),
        "initial_service_boundary": "가격 표시·계산 지원 전용 · 요금 정책 변경·자동 환불 없음",
    },
    "stage2_feature_structure": {
        "input": "확정된 배송 주소와 장바구니 구성",
        "decision": "요금 규칙으로 배송비·수수료를 분해 계산하고 산정 사유와 신뢰도를 판단",
        "output": "고객이 주문 전 확인한 배송비 분해 안내와 예상가-실제가 정산 로그",
    },
    "stage2_in_scope": [
        "주소·장바구니 기준 예상 배송비 분해 계산",
        "산정 사유 문구·예상 범위 노출",
        "예상가-실제가 차이 감지/플래그",
        "이탈·문의 평가용 노출 로그",
    ],
    "stage2_out_scope": [
        "요금 정책 자동 변경·할인",
        "불일치 자동 환불/보상",
        "개인화 동적 가격 최적화",
    ],
    "stage2_open_questions": [
        "어느 단계부터 사전 안내를 노출해 이탈을 가장 줄일 것인가?",
        "예상가와 실제가 차이를 어느 범위까지 '일치'로 허용할 것인가?",
    ],
    "stage2_service_blocks": [
        "요금 규칙·주소 데이터 수집",
        "예상가 분해 계산",
        "사유 문구·안내 카드 렌더러",
        "예상가-실제가 정산 로그 저장소",
    ],
    "verify_guardrails": [
        "요금 데이터 신뢰도가 낮으면 단일 금액 대신 예상 범위로만 노출한다",
        "예상가-실제가 차이가 허용 범위를 넘으면 노출을 멈추고 운영자 확인 큐로 보낸다",
        "장바구니 이탈률과 배송비 관련 CS 문의를 매일 모니터링한다",
    ],
    "verify_scope_keywords": ["auto_pricing", "auto_refund"],
}


_MERCHANT_PREP: Dict[str, Any] = {
    "one_page_focus": (
        "기사 도착 전 매장 준비 지연을 신호로 드러내고 사장님이 알린 예상 준비시간을 배차 "
        "타이밍에 참고로 반영하는, 기존 매장 주문 화면 개선형 MVP로 정리한다. "
        "단 배차 확정은 사람/운영이 쥔다."
    ),
    "problem": {
        "customer_pain": (
            "기사는 매장 앞에서 5~10분씩 헛대기를 하며 다음 콜을 못 잡고, 고객은 그 대기가 "
            "더해진 만큼 늦은 배송을 받는다."
        ),
        "business_impact": (
            "매장 준비 지연이 배차에 반영되지 않아 기사 헛대기와 배송 지연으로 전가되고, "
            "상습 지연 매장이 사후 컴플레인으로만 드러나 선제 관리와 매장 코칭 시점을 놓친다."
        ),
        "current_workaround": (
            "운영팀이 컴플레인이 터진 뒤에야 해당 매장을 수동으로 들여다보고, 사장님 주문 "
            "화면엔 신규 주문만 떠서 준비가 얼마나 걸리는지 양쪽 모두 알 수 없다."
        ),
        "success_criteria": [
            "기사 도착 시점에 매장 준비 진행/지연 상태를 운영자와 기사가 함께 확인한다.",
            "사장님이 표시한 예상 준비시간과 평소보다 느림 신호가 배차 타이밍 참고값으로 전달되고 로그로 남는다.",
            "매장에 보이는 신호가 감시가 아니라 준비를 돕는 톤으로, 과장 없이 운영 정책과 일치한다.",
        ],
    },
    "personas": [
        {
            "name": "매장 사장님(가맹점주)",
            "role": "merchant_owner",
            "needs": [
                "신규 주문만이 아니라 이건 15분 걸려요를 한 번에 알릴 수 있으면 좋겠다.",
                "느린 매장으로 감시당하는 느낌 없이 준비 상황을 솔직히 알리고 싶다.",
            ],
        },
        {
            "name": "매장 운영 담당자",
            "role": "merchant_operations_manager",
            "needs": [
                "어느 매장이 늘 늦는지 컴플레인 전에 데이터로 보고 싶다.",
                "지연이 매장 기인인지 기사/외부 기인인지 구분해 코칭 대상을 정하고 싶다.",
            ],
        },
    ],
    "scope_in": [
        "기존 매장 주문 화면에 준비 진행 상태/예상 준비시간 표시 추가",
        "평소 대비 느림 등 매장 지연 신호 산출과 노출",
        "사장님 예상 준비시간 입력을 배차 타이밍 참고값으로 전달",
        "상습 지연 매장 가시화와 준비시간/대기 이벤트 로그 집계",
    ],
    "scope_out": [
        "준비시간 신호만으로 자동 배차 확정/콜 취소",
        "매장 평가에 따른 자동 패널티·노출 순위 자동 조정",
        "사장님 입력 없이 조리 완료 시점 자동 판정",
    ],
    "screen": {
        "name": "매장 준비현황 패널(매장 주문 화면 개선)",
        "purpose": (
            "사장님이 신규 주문과 함께 준비 진행/예상 준비시간을 한 화면에서 보고 알리며, "
            "평소보다 느림 신호를 부담 없이 인지한다."
        ),
        "primary_user": "매장 사장님(가맹점주)",
        "entry_point": "매장 주문 앱 > 진행 중 주문 > 준비현황(기존 신규 주문 목록에 탭/패널 추가)",
        "components": [
            "주문별 준비 경과시간 표시",
            "이건 N분 걸려요 예상 준비시간 입력 버튼",
            "평소보다 느림 안내 배지(부드러운 톤)",
            "기사 도착 예정/도착 표시",
            "오늘 준비시간 요약(스스로 보는 자가 진단)",
        ],
        "primary_actions": ["예상 준비시간 표시", "준비 완료 알림", "지연 사유 선택"],
        "empty_states": [
            "진행 중 주문이 없을 때 준비현황을 비우고 신규 주문 대기 안내를 표시"
        ],
        "error_states": [
            "기사 도착 이벤트나 주문 상태 동기화가 지연되면 도착 정보 갱신 지연 배지를 표시하고 준비시간 입력은 계속 허용"
        ],
        "acceptance_criteria": [
            "준비 경과시간과 사장님 표시 예상 준비시간이 한 화면에서 함께 보인다.",
            "예상 준비시간 표시와 지연 사유 선택이 사유와 매장 ID와 함께 이벤트 로그에 저장된다.",
            "평소보다 느림 배지는 비난 문구 없이 표시되고, 표시 기준을 사장님이 안내받을 수 있다.",
        ],
    },
    "policy": {
        "name": "매장 지연 신호 노출·반영 기준",
        "trigger": (
            "주문 접수 후 준비 경과시간이 해당 매장 평소 분포 또는 사장님 표시 시간을 넘기는 "
            "신호가 감지된 경우"
        ),
        "rule": (
            "지연 신호와 사장님 표시 준비시간은 배차 타이밍의 참고값으로만 전달하고, 매장에는 "
            "비난이 아닌 준비 도움 톤으로 노출한다. 배차 확정·콜 취소는 운영/시스템 정책이 "
            "별도로 결정한다."
        ),
        "owner": "매장운영기획",
        "exception_handling": (
            "매장 표본이 적거나 도착 이벤트가 지연되면 평소보다 느림 신호 대신 확인 필요 "
            "상태로 표시하고 자동 반영을 보류한다."
        ),
    },
    "metrics": [
        {
            "name": "기사 매장 평균 대기시간",
            "baseline": "최근 2주 동일 매장군 도착~픽업 평균 7.5분",
            "target": "파일럿 기간 3분 이하로 단축",
            "measurement": "기사 도착 이벤트와 픽업 완료 시각 차이를 매장 기준으로 집계",
            "owner": "운영기획",
        },
        {
            "name": "매장 기인 배송 지연 비율",
            "baseline": "최근 2주 매장 준비 기인 지연 38%",
            "target": "파일럿 기간 20% 이하로 감소",
            "measurement": "지연 사유 코드(매장 준비/기사/외부)와 SLA 초과 주문을 조인",
            "owner": "매장운영기획",
        },
    ],
    "data_requirements": [
        {
            "source": "매장 주문 상태 스트림",
            "purpose": "주문 접수·조리 시작·완료 시각으로 준비 경과시간을 계산",
            "freshness": "30초 이내",
            "quality_rule": "주문 ID와 상태 변경 시각, 매장 ID는 필수",
        },
        {
            "source": "기사 도착 이벤트(기사 앱)",
            "purpose": "도착 시점과 대기시간을 측정하고 매장 화면 도착 표시에 사용",
            "freshness": "30초 이내",
            "quality_rule": "도착 지오펜스 판정 기준과 도착 시각을 함께 저장",
        },
        {
            "source": "매장 준비시간 기준 프로필",
            "purpose": "매장별 평소 준비시간 분포로 평소보다 느림 신호를 산출",
            "freshness": "일 단위 재계산",
            "quality_rule": "표본 수가 기준 미만이면 신호를 보류하고 매장 동의 범위를 보관",
        },
    ],
    "event_prefix": "prep",
    "event_logs": [
        {
            "event_name": "prep_time_signal_shown",
            "trigger": "매장 화면 또는 운영 콘솔에 준비 지연/평소보다 느림 신호가 노출됨",
            "properties": [
                "order_id",
                "merchant_id",
                "elapsed_minutes",
                "baseline_minutes",
                "signal_level",
            ],
            "purpose": "지연 신호 노출 빈도와 상습 지연 매장 식별 정확도 분석",
        },
        {
            "event_name": "prep_time_estimate_set",
            "trigger": "사장님이 예상 준비시간을 표시하거나 지연 사유를 선택함",
            "properties": [
                "order_id",
                "merchant_id",
                "estimated_minutes",
                "delay_reason",
                "created_at",
            ],
            "purpose": "사장님 표시 준비시간 정확도와 배차 타이밍 반영 효과 분석",
        },
    ],
    "impl_slice": {
        "name": "매장 준비현황 패널 + 신호 반영 MVP",
        "scope": [
            "준비 경과시간 산출 API",
            "매장 주문 화면 준비현황 패널 추가",
            "예상 준비시간/지연 신호 이벤트 저장과 배차 참고값 전달",
        ],
        "owner_hint": "백엔드/프론트엔드(매장 앱)/데이터",
        "acceptance_criteria": [
            "샘플 주문·도착 데이터로 준비 경과시간과 평소보다 느림 신호가 재현된다.",
            "사장님 표시 준비시간이 배차 타이밍 참고값으로 전달되고 대기시간 KPI 계산에 사용된다.",
        ],
    },
    "decision_agenda": {
        "topic": "지연 신호 노출 톤과 파일럿 매장군",
        "decision_needed": (
            "평소보다 느림 신호를 매장에 어디까지 보여줄지(매장 본인만 vs 운영팀 공유)와 "
            "첫 파일럿 매장군을 확정"
        ),
        "owner": "매장운영 리드",
        "options": [
            "상습 지연 상위 매장군",
            "신규 입점 매장군",
            "단일 카테고리(예: 치킨/분식) 매장군",
        ],
    },
    "open_question": {
        "question": (
            "매장 표본이 적거나 피크에 몰릴 때 평소보다 느림 기준을 어떻게 잡아야 사장님이 "
            "부당하다고 느끼지 않는가?"
        ),
        "owner": "매장운영기획",
        "needed_by": "개발 착수 전",
    },
    "developer_handoff": [
        "준비시간 신호만으로 자동 배차 확정·콜 취소는 이번 범위에서 제외하고, 참고값 전달까지만 구현한다.",
        "매장 화면 신호는 비난 문구 없이 준비 도움 톤으로 노출하고, 표시 기준을 사장님이 안내받을 수 있어야 한다.",
        "예상 준비시간/지연 신호 이벤트는 대기시간·매장 기인 지연 KPI 분석의 기준 로그로 사용한다.",
    ],
    "stage1_problem_summary": (
        "매장 준비시간 지연 가시화는 기사 헛대기와 매장 기인 배송 지연을 줄이기 위해, 기존 "
        "매장 주문 화면이 신규 주문만 보여주는 현 상태를 넘어 준비 진행·지연 신호를 사장님과 "
        "운영자가 함께 보고 배차 타이밍에 참고로 반영하는 것을 목표로 한다."
    ),
    "stage1_scope_candidates": [
        "매장 주문 화면 준비현황 표시",
        "평소보다 느림 매장 지연 신호",
        "사장님 예상 준비시간 입력 로그",
    ],
    "stage1_engineer": {
        "data_readiness_question": (
            "매장 주문 상태와 기사 도착 이벤트를 주문·매장 기준으로 시간대별 조인할 수 있는가, "
            "그리고 매장별 평소 준비시간 분포를 만들 표본이 충분한가?"
        ),
        "initial_service_boundary": "준비 가시화·배차 타이밍 참고값 제공 전용 · 자동 배차 확정/콜 취소 없음",
    },
    "stage2_feature_structure": {
        "input": "매장 주문 상태와 기사 도착 이벤트, 매장별 평소 준비시간 분포",
        "decision": (
            "준비 경과를 매장 기준선·사장님 표시 시간과 비교해 지연 신호를 산출하고 배차 "
            "타이밍 참고값을 제안"
        ),
        "output": (
            "매장 화면 준비현황·지연 신호와 운영자가 보는 상습 지연 매장 가시화, "
            "그리고 배차 참고값 로그"
        ),
    },
    "stage2_in_scope": [
        "주문별 준비 경과시간 산출",
        "평소보다 느림 매장 지연 신호 노출",
        "사장님 예상 준비시간/지연 사유 입력",
        "상습 지연 매장 가시화와 대기/지연 평가용 로그",
    ],
    "stage2_out_scope": [
        "준비시간 기반 자동 배차 확정/콜 취소",
        "매장 자동 패널티·노출 순위 자동 조정",
        "사장님 입력 없는 조리 완료 자동 판정",
    ],
    "stage2_open_questions": [
        "평소보다 느림 신호를 매장 본인에게만 보일지 운영팀과 공유할지 어떻게 결정할 것인가?",
        "매장 표본이 적은 신규/피크 상황에서 기준선을 어떻게 보정할 것인가?",
    ],
    "stage2_service_blocks": [
        "주문·도착 이벤트 수집",
        "매장 준비시간 기준선/신호 산출",
        "매장 준비현황 패널 렌더러",
        "예상 준비시간·신호 이벤트 저장소",
    ],
    "verify_guardrails": [
        "준비시간 신호는 배차 참고값까지만 쓰고 자동 배차 확정·콜 취소는 사람/운영이 결정한다",
        "매장 표본 부족·도착 이벤트 지연 시 평소보다 느림 신호 대신 확인 필요로 보류한다",
        "기사 대기시간과 매장 기인 지연 비율, 그리고 매장 불만 신호를 매일 모니터링한다",
    ],
    "verify_scope_keywords": ["auto_dispatch", "merchant_penalty"],
}


_CS_TRIAGE: Dict[str, Any] = {
    "one_page_focus": (
        "지금 채팅 채널이 모든 문의를 상담사에게 그대로 넘기는 구조를, 반복 문의는 자동 "
        "분류·1차 응대하고 화난 고객·분쟁만 상담사로 넘기는 분류형 MVP로 정리한다."
    ),
    "problem": {
        "customer_pain": (
            "고객은 내 배송 어디쯤이냐는 단순 질문에도 상담사 연결을 한참 기다리고, 정작 "
            "환불·분쟁처럼 급한 일은 더 오래 밀린다."
        ),
        "business_impact": (
            "반복 문의가 상담 인력을 묶어 환불·분쟁 같은 고난도 응대가 지연되고, 대기 길어진 "
            "고객의 이탈과 클레임 격화 비용이 커진다."
        ),
        "current_workaround": (
            "지금 채팅 채널은 모든 문의를 구분 없이 상담사 큐로 넘기고, 상담사가 일일이 "
            "주문을 찾아 손으로 같은 답을 반복한다."
        ),
        "success_criteria": [
            "배송 위치·연락처 같은 반복 문의는 상담사 개입 없이 1차 응대된다.",
            "화난 고객·환불·분쟁 신호가 있으면 자동 응대하지 않고 상담사로 넘긴다.",
            "자동 분류 결과와 상담사 전달 사유가 모두 로그로 남는다.",
        ],
    },
    "personas": [
        {
            "name": "CS 운영 매니저",
            "role": "cs_operations_manager",
            "needs": [
                "반복 문의를 덜어 상담사가 고난도 건에 집중하게 하고 싶다.",
                "자동 응대 경계와 상담사 전달 기준을 직접 정하고 싶다.",
            ],
        },
        {
            "name": "1선 상담사",
            "role": "cs_agent",
            "needs": [
                "로봇 같은 오답이 고객을 더 화나게 만들지 않게 하고 싶다.",
                "넘어온 문의의 분류 사유와 주문 맥락을 한눈에 보고 싶다.",
            ],
        },
    ],
    "scope_in": [
        "유입 문의 의도 자동 분류",
        "반복 문의 주문정보 기반 1차 응대",
        "고난도·긴급 문의 상담사 전달 큐",
        "분류·전달 결과 로그와 KPI 집계",
    ],
    "scope_out": [
        "환불/보상 자동 승인·지급",
        "상담 시스템 전면 교체",
        "고객 감정 자동 진정·자동 사과 종결",
    ],
    "screen": {
        "name": "문의 분류·상담사 전달 콘솔",
        "purpose": "유입 문의가 어떻게 분류돼 1차 응대됐는지 보고, 상담사 전달 큐와 경계를 관리한다.",
        "primary_user": "CS 운영 매니저",
        "entry_point": "상담 콘솔 > 채팅 운영 > 문의 분류 현황",
        "components": [
            "의도 분류 라벨/신뢰도 컬럼",
            "주문정보 연결 1차 응답 미리보기",
            "상담사 전달 큐(고난도/긴급)",
            "전달 사유·분류 신뢰도 배지",
            "자동 처리율/오분류율 KPI",
        ],
        "primary_actions": ["상담사 직접 인계", "1차 응답 문구 수정", "문의 상세·주문 맥락 확인"],
        "empty_states": ["현재 상담사 전달이 필요한 문의가 없음을 표시"],
        "error_states": [
            "주문정보 조회가 지연되면 자동 응답 대신 분류 신뢰도 낮음 배지를 표시하고 상담사 큐로 보냄"
        ],
        "acceptance_criteria": [
            "문의는 의도 라벨과 분류 신뢰도순으로 정렬된다.",
            "1차 응답 발송과 상담사 전달 시 사유·라벨이 이벤트 로그에 저장된다.",
            "분노/분쟁 신호나 낮은 신뢰도면 자동 응대하지 않고 상담사로 넘긴다.",
        ],
    },
    "policy": {
        "name": "자동 응대·상담사 전달 경계 기준",
        "trigger": "채팅 채널로 새 문의가 유입되어 의도가 분류된 시점",
        "rule": (
            "배송 위치·연락처 등 반복 의도는 신뢰도 임계치 이상일 때만 주문정보 기반 1차 "
            "응대하고, 환불·분쟁·분노 신호나 낮은 신뢰도는 자동 응대 없이 상담사 큐로 전달한다."
        ),
        "owner": "CS운영기획",
        "exception_handling": (
            "분류 신뢰도가 낮거나 주문정보 조회가 실패하면 자동 응답을 보류하고 상담사 확인 "
            "단계를 둔다."
        ),
    },
    "metrics": [
        {
            "name": "반복 문의 자동 처리율",
            "baseline": "최근 2주 반복 단순 문의 중 상담사 수기 응대 비율 100%",
            "target": "파일럿 기간 자동 1차 처리율 60% 이상",
            "measurement": "의도 라벨별 문의 수와 자동 1차 응답 종결 건수를 조인",
            "owner": "CS운영기획",
        },
        {
            "name": "긴급 클레임 1차 응대 시간",
            "baseline": "최근 2주 환불·분쟁 문의 1차 응대까지 평균 18분",
            "target": "파일럿 기간 6분 이내로 단축",
            "measurement": "긴급 라벨 문의의 유입 시각과 상담사 1차 응답 시각 차이 집계",
            "owner": "CS운영",
        },
    ],
    "data_requirements": [
        {
            "source": "채팅 문의 메시지 로그",
            "purpose": "유입 문의 의도를 분류하고 반복 패턴을 식별",
            "freshness": "실시간(10초 이내)",
            "quality_rule": "대화 ID·발화 시각·고객 식별자를 필수로 보관하고 민감정보는 마스킹",
        },
        {
            "source": "주문 상태 조회 API",
            "purpose": "배송 위치·연락처 등 1차 응답에 넣을 주문 사실을 연결",
            "freshness": "30초 이내",
            "quality_rule": "주문 ID 매핑 정합성과 조회 실패 시 fallback 사유를 기록",
        },
        {
            "source": "상담사 전달·종결 이력",
            "purpose": "오분류와 상담사 재배정, 자동 처리 효과를 측정",
            "freshness": "시간 단위",
            "quality_rule": "분류 라벨과 최종 처리 결과 매핑을 표준 코드로 보관",
        },
    ],
    "event_prefix": "cs",
    "event_logs": [
        {
            "event_name": "cs_inquiry_classified",
            "trigger": "채팅 문의가 유입되어 의도 라벨이 부여된 시점",
            "properties": ["inquiry_id", "intent_label", "confidence", "order_id", "auto_handled"],
            "purpose": "분류 분포와 자동 처리 대상 판단, 신뢰도 임계치 튜닝",
        },
        {
            "event_name": "cs_inquiry_handed_off",
            "trigger": "고난도·긴급 또는 낮은 신뢰도로 상담사 큐에 전달된 시점",
            "properties": [
                "inquiry_id",
                "handoff_reason",
                "intent_label",
                "agent_id",
                "created_at",
            ],
            "purpose": "오분류율, 전달 사유 분포, 긴급 클레임 응대 시간 분석",
        },
    ],
    "impl_slice": {
        "name": "문의 분류·1차 응대 라우팅 MVP",
        "scope": [
            "의도 분류 API",
            "주문정보 연결 1차 응답 렌더링",
            "상담사 전달 큐·이벤트 저장",
        ],
        "owner_hint": "백엔드/프론트엔드/데이터",
        "acceptance_criteria": [
            "샘플 채팅 로그로 반복 문의 자동 분류·1차 응답이 재현된다.",
            "분류·전달 로그가 자동 처리율/오분류율 KPI 계산에 사용된다.",
        ],
    },
    "decision_agenda": {
        "topic": "자동 응대 대상 의도와 상담사 전달 경계",
        "decision_needed": (
            "어떤 의도 라벨까지 자동 1차 응대하고, 어떤 신호부터 무조건 상담사로 넘길지 확정"
        ),
        "owner": "CS운영 리드",
        "options": [
            "배송 위치·연락처만 자동 응대",
            "단순 조회 전반 자동 응대",
            "분노·분쟁 키워드는 무조건 상담사 인계",
        ],
    },
    "open_question": {
        "question": "분류 신뢰도가 낮을 때 자동 1차 응답을 어디까지 허용하고 언제 상담사로 넘길 것인가?",
        "owner": "CS운영기획",
        "needed_by": "개발 착수 전",
    },
    "developer_handoff": [
        "상담사 확인 없는 환불·보상 자동 승인은 이번 범위에서 제외한다.",
        "모든 자동 1차 응답은 분류 라벨과 신뢰도, 사용한 주문정보 출처를 함께 노출한다.",
        "분노·분쟁 신호나 낮은 신뢰도는 자동 응대하지 않고 상담사 큐로 전달하는 것을 기본값으로 한다.",
    ],
    "stage1_problem_summary": (
        "반복 배송 문의 자동 분류·1차 응대는 환불·분쟁 같은 고난도 응대 지연을 줄이기 위해, "
        "채팅 채널의 반복 단순 문의를 자동으로 분류해 1차 처리하고 진짜 사람이 필요한 건만 "
        "상담사로 넘기는 것을 목표로 한다."
    ),
    "stage1_scope_candidates": [
        "유입 문의 의도 자동 분류",
        "반복 문의 주문정보 기반 1차 응답",
        "고난도·긴급 문의 상담사 전달 로그",
    ],
    "stage1_engineer": {
        "data_readiness_question": (
            "채팅 문의 메시지를 주문 상태 조회 결과와 대화/주문 ID 기준으로 실시간 연결할 수 있는가?"
        ),
        "initial_service_boundary": "분류·1차 응대 지원 전용 · 환불/보상 자동 처리 없음",
    },
    "stage2_feature_structure": {
        "input": "채팅으로 유입된 고객 문의와 연결된 주문 상태",
        "decision": "문의 의도를 분류하고 반복 문의면 1차 응답, 고난도·긴급이면 상담사 전달을 판단",
        "output": "자동 1차 응답 또는 상담사 전달 큐 항목과 분류·전달 로그",
    },
    "stage2_in_scope": [
        "유입 문의 의도 분류·신뢰도 산출",
        "주문정보 연결 반복 문의 1차 응답",
        "고난도·긴급 문의 상담사 전달 액션",
        "오분류·자동 처리율 평가용 로그",
    ],
    "stage2_out_scope": [
        "환불/보상 자동 승인·지급",
        "상담 시스템 전면 교체",
        "고객 감정 자동 진정·자동 종결",
    ],
    "stage2_open_questions": [
        "어떤 의도 라벨까지 자동 1차 응대를 발동할 것인가?",
        "분노·분쟁 신호와 낮은 신뢰도를 어떤 기준으로 상담사 전달로 강제할 것인가?",
    ],
    "stage2_service_blocks": [
        "문의 수집·전처리",
        "의도 분류기",
        "주문정보 연결 응답 렌더러",
        "상담사 전달 큐·이벤트 저장소",
    ],
    "verify_guardrails": [
        "분류 신뢰도가 낮으면 자동 응대 대신 상담사 확인을 둔다",
        "분노·분쟁·환불 신호는 자동 응대하지 않고 상담사로 전달한다",
        "오분류율과 긴급 클레임 1차 응대 시간을 매일 모니터링한다",
    ],
    "verify_scope_keywords": ["auto_resolve", "dispute_automation"],
}


_PROFILES: Dict[str, Dict[str, Any]] = {
    "dispatch_recommendation": _DISPATCH,
    "eta_prediction": _ETA,
    "failed_delivery_risk": _FAILED,
    "rider_onboarding_dropout": _RIDER_ONBOARDING,
    "return_pickup_flow": _RETURN_PICKUP,
    "checkout_fee_transparency": _CHECKOUT_FEE,
    "merchant_prep_visibility": _MERCHANT_PREP,
    "cs_repeat_inquiry_triage": _CS_TRIAGE,
}


def get_scenario_profile(scenario: str) -> Dict[str, Any]:
    """Return the copy profile for a scenario, falling back to dispatch."""
    return _PROFILES.get(scenario, _DISPATCH)


def scenario_keys() -> List[str]:
    return list(_PROFILES.keys())
