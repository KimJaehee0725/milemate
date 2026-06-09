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


_PROFILES: Dict[str, Dict[str, Any]] = {
    "dispatch_recommendation": _DISPATCH,
    "eta_prediction": _ETA,
    "failed_delivery_risk": _FAILED,
}


def get_scenario_profile(scenario: str) -> Dict[str, Any]:
    """Return the copy profile for a scenario, falling back to dispatch."""
    return _PROFILES.get(scenario, _DISPATCH)


def scenario_keys() -> List[str]:
    return list(_PROFILES.keys())
