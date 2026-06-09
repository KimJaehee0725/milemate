from __future__ import annotations

import base64
import json
import os
import sys
import time
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterable
from urllib import error, request
from xml.sax.saxutils import escape

import streamlit as st
import yaml
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.frontend.demo_backend import LocalDemoAPI  # noqa: E402
from app.frontend.demo_data import (  # noqa: E402
    VERIFICATION_PRESETS,
    load_demo_inputs,
    scenario_title,
    verification_context_for_preset,
)

API_BASE_URL = os.getenv("MILEMATE_API_BASE", "http://127.0.0.1:8000").rstrip("/")
API_MODE = os.getenv("MILEMATE_API_MODE", "http")
API_TIMEOUT_SECONDS = float(os.getenv("MILEMATE_API_TIMEOUT_SECONDS", "620"))
LOADING_CAT_SPRITE_PATH = Path(__file__).resolve().parent / "assets" / "loading-cat-yarn-sprite.png"
STAGE_IDS = ("stage_1", "stage_2", "stage_3", "stage_4")
DECISION_STATUS_LABELS = {
    "proposed": "제안",
    "approved": "승인",
    "deferred": "보류",
    "rejected": "반려",
}
RISK_CATEGORY_LABELS = {
    "data": "데이터",
    "technical": "기술",
    "operational": "운영",
    "regulatory": "규제",
    "scope": "범위",
    "other": "기타",
}
SEVERITY_LABELS = {
    "low": "낮음",
    "medium": "중간",
    "high": "높음",
}
STAGE_STATUS_STYLE = {
    "승인 완료": ("✅", "done"),
    "승인 대기": ("🕓", "review"),
    "작업 중": ("🔵", "active"),
    "생성 완료": ("◽", "generated"),
    "대기": ("⚪", "pending"),
}
PDF_FONT_CANDIDATES = [
    (
        "MilemateNanum",
        "/Library/Fonts/NanumGothic.ttf",
        "/Library/Fonts/NanumGothicBold.ttf",
    ),
    (
        "MilematePretendard",
        "/Users/jaeheemacbook/Library/Fonts/Pretendard-Regular.ttf",
        "/Users/jaeheemacbook/Library/Fonts/Pretendard-Bold.ttf",
    ),
]

DEFAULT_DEMO_STAGE_REQUESTS: Dict[str, str] = {
    "stage_1": (
        "지금 서비스에서 어디가 막히는지 팀이 바로 논의할 수 있게 정리해주세요. "
        "고객이 실제로 불편을 느끼는 순간, 운영팀이 매일 확인하는 지표, 비용이 "
        "새는 구간, 고객 안내나 프로모션에서 조심해야 할 표현까지 같이 보고 싶습니다."
    ),
    "stage_2": (
        "이번 MVP는 오늘 회의에서 범위를 확정할 수 있을 정도로 구체적이면 좋겠습니다. "
        "고객에게 먼저 보여줄 경험, 운영팀이 감당할 수 있는 업무량, 비용을 줄이는 "
        "우선순위, 외부에 말할 수 있는 서비스 약속을 함께 잡아주세요."
    ),
    "stage_3": (
        "이 안을 바로 밀어붙였을 때 운영팀이 감당하기 어려운 지점이 있는지 보고 "
        "싶습니다. 수요가 예상과 다르거나 비용이 더 커지는 경우, 고객 안내가 "
        "과장되어 보이는 경우, 현장에서 보류해야 할 조건을 확인해주세요."
    ),
    "stage_4": (
        "교수님께 시연할 때 서비스 기획안처럼 설명할 수 있게 정리해주세요. 어떤 "
        "고객 문제를 먼저 풀고, 운영팀은 무엇을 바꾸고, 비용은 어디서 줄고, "
        "고객에게는 어떤 약속을 할 수 있는지 한 흐름으로 보여주면 좋겠습니다."
    ),
}

DEMO_STAGE_REQUESTS: Dict[str, Dict[str, str]] = {
    "dispatch_recommendation": {
        "stage_1": (
            "강남/서초 피크타임에 주문이 한꺼번에 들어오면 일부 배송원에게 배차가 "
            "몰리고, 늦은 주문은 CS 문의와 쿠폰 비용으로 이어지고 있습니다. 운영팀이 "
            "어느 구역과 어떤 주문을 먼저 봐야 하는지 판단할 수 있게 문제를 잡아주세요. "
            "고객에게는 왜 늦는지보다 언제 해결되는지가 중요하므로 안내 기준과 신뢰 "
            "지표도 같이 보고 싶습니다."
        ),
        "stage_2": (
            "이번 MVP에서는 운영자가 피크타임에 위험 주문을 빠르게 확인하고 추천 "
            "사유를 본 뒤 승인하거나 보류하는 흐름까지만 보여주고 싶습니다. 완전 자동 "
            "배차는 아직 부담스럽고, 배송원 반발이나 매장 클레임을 줄일 수 있는 운영 "
            "화면과 정책 문구가 먼저 필요합니다. 지연률, SLA, 배송원 편차, 보상 비용을 "
            "같이 볼 수 있게 범위를 잡아주세요."
        ),
        "stage_3": (
            "주문 상태나 배송원 위치가 조금만 늦게 들어와도 추천이 틀릴 수 있고, "
            "운영자가 추천을 믿지 않으면 화면이 있어도 쓰지 않을 것 같습니다. 피크타임 "
            "수요가 예상보다 크거나 배송원 공급이 부족할 때 비용과 고객 안내가 어떻게 "
            "흔들리는지 확인해주세요. 데이터가 부족하면 어떤 판단은 보류해야 하는지도 "
            "알려주세요."
        ),
        "stage_4": (
            "최종 설명에서는 피크타임에 밀리는 주문을 먼저 발견하고 운영자가 납득할 "
            "수 있는 추천으로 지연 비용을 줄인다는 메시지가 분명했으면 합니다. 고객 "
            "신뢰, 배송원 운영, 매장 클레임, 비용 절감 효과를 하나의 서비스 시나리오로 "
            "말할 수 있게 정리해주세요."
        ),
    },
    "eta_prediction": {
        "stage_1": (
            "고객은 도착 시간을 신뢰하고 기다리는데, ETA가 계속 바뀌거나 지연 안내가 "
            "늦으면 바로 문의와 불만으로 이어집니다. 지금 문제는 예측 정확도 자체도 "
            "있지만, 운영팀이 언제 고객에게 먼저 알릴지 판단하지 못하는 데도 있습니다. "
            "고객 문의를 줄이고 브랜드 신뢰를 지키는 서비스 문제로 잡아주세요."
        ),
        "stage_2": (
            "이번 MVP에서는 지연 가능성이 높은 주문을 운영자가 먼저 보고, 고객에게 "
            "보낼 안내 문구와 알림 타이밍을 확인하는 흐름을 보여주고 싶습니다. 자동 "
            "보상이나 정교한 마케팅 캠페인은 뒤로 미루고, 문의 감소와 고객 불안 완화에 "
            "바로 도움이 되는 범위부터 잡아주세요. 운영팀이 하루에 볼 수 있는 업무량도 "
            "같이 고려해주세요."
        ),
        "stage_3": (
            "실시간 위치나 이동 이력이 늦게 들어오면 알림이 과하게 나가거나 너무 "
            "늦게 나갈 수 있습니다. 고객에게 자주 알리면 피로도가 생기고, 적게 알리면 "
            "신뢰가 떨어집니다. 수요가 몰리는 시간대, CS 비용, 마케팅 약속, 개인정보 "
            "이슈까지 포함해서 이 기획이 어디서 흔들릴 수 있는지 점검해주세요."
        ),
        "stage_4": (
            "최종 설명은 늦기 전에 알려서 고객 문의와 불만을 줄이고, 운영팀이 먼저 "
            "대응하게 만든다는 방향이면 좋겠습니다. 고객 경험, 운영 비용, 브랜드 신뢰, "
            "알림 정책을 서비스 기획안처럼 자연스럽게 연결해주세요."
        ),
    },
    "failed_delivery_risk": {
        "stage_1": (
            "배송 실패는 고객 불편뿐 아니라 재배송비, 상담 시간, 매장과 기사 조율 "
            "비용까지 같이 키우고 있습니다. 실패가 난 뒤 처리하는 방식보다 실패 가능성이 "
            "높은 주문을 미리 발견해서 운영팀이 한 번 더 확인하는 서비스가 필요합니다. "
            "어떤 고객 상황과 주문 조건을 먼저 봐야 하는지 기획 관점에서 잡아주세요."
        ),
        "stage_2": (
            "이번 MVP에서는 실패 위험이 높은 주문을 운영팀이 큐에서 확인하고, 연락 "
            "필요 여부나 사전 확인 액션을 선택하는 흐름을 보여주고 싶습니다. 자동 고객 "
            "연락은 아직 조심스럽고, 상담팀이 실제로 처리할 수 있는 업무량과 고객 "
            "불쾌감을 줄이는 문구가 중요합니다. 재배송비와 운영 손실을 줄이는 범위로 "
            "정리해주세요."
        ),
        "stage_3": (
            "위험 주문을 너무 많이 띄우면 운영팀 업무가 늘고 고객에게 불필요한 연락이 "
            "갈 수 있습니다. 반대로 너무 적게 띄우면 실패 배송 비용이 그대로 남습니다. "
            "고객 응답 이력, 주문 특성, 상담팀 처리 여력, 개인정보 민감도를 기준으로 "
            "어떤 경우에 개입을 줄이거나 보류해야 하는지 점검해주세요."
        ),
        "stage_4": (
            "최종 설명은 실패가 난 뒤 수습하는 서비스가 아니라 실패 가능성을 미리 "
            "낮추는 운영 서비스로 보이면 좋겠습니다. 고객 경험, 상담팀 업무량, 재배송 "
            "비용, 매장 신뢰를 함께 개선하는 기획안으로 정리해주세요."
        ),
    },
}


@st.cache_resource
def local_demo_api() -> LocalDemoAPI:
    return LocalDemoAPI()


def api_request(method: str, path: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if API_MODE == "local":
        return local_demo_api().request(method=method, path=path, payload=payload)

    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{API_BASE_URL}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=API_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"{exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"백엔드에 연결할 수 없습니다: {API_BASE_URL} ({exc.reason})") from exc


@st.cache_data
def load_scenarios() -> Dict[str, Dict[str, Any]]:
    with open(ROOT_DIR / "config" / "scenarios.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["scenarios"]


@st.cache_data
def load_demo_input_map() -> Dict[str, Dict[str, Any]]:
    return load_demo_inputs(ROOT_DIR)


def render_list(items: Iterable[Any]) -> None:
    for item in items:
        st.markdown(f"- {item}")


def display_value(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(display_value(item) for item in value)
    if isinstance(value, dict):
        return ", ".join(
            f"{format_label(str(key))}: {display_value(item)}"
            for key, item in value.items()
        )
    if value is None:
        return "없음"
    return str(value)


def render_value(value: Any) -> None:
    if isinstance(value, dict):
        rows = [
            {"구분": format_label(str(key)), "내용": display_value(item)}
            for key, item in value.items()
        ]
        st.dataframe(rows, width="stretch", hide_index=True)
    elif isinstance(value, list):
        if value and all(isinstance(item, dict) for item in value):
            st.dataframe(value, width="stretch", hide_index=True)
        else:
            rows = [{"항목": display_value(item)} for item in value]
            st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.write(value)


def render_key_values(data: Dict[str, Any]) -> None:
    if not data:
        st.info("아직 표시할 항목이 없습니다.")
        return
    for key, value in data.items():
        with st.container(border=True):
            st.markdown(f"**{format_label(key)}**")
            render_value(value)


def format_label(value: str) -> str:
    labels = {
        "Current stage": "현재 단계",
        "Approved": "승인됨",
        "Outputs": "생성 결과",
        "problem_redefinition": "문제 재정의",
        "target_users": "대상 사용자",
        "prioritized_kpis": "우선 KPI",
        "mvp_scope": "MVP 범위",
        "expected_value": "기대 효과",
        "required_data": "필요 데이터",
        "required_tech_blocks": "필요 기술 블록",
        "constraints": "제약 조건",
        "implementation_order": "구현 순서",
        "verification_plan": "검증 계획",
        "graph_runtime": "그래프 런타임",
        "problem_summary": "문제 요약",
        "feature_structure": "서비스 구조",
        "mvp_in_scope": "이번 범위",
        "mvp_out_of_scope": "제외 범위",
        "open_questions": "확인 질문",
        "kpi_candidates": "후보 KPI",
        "scope_candidates": "후보 범위",
        "verifier_status": "검증 상태",
        "rollback_recommendation": "롤백 권고",
        "service_blocks": "서비스 블록",
        "primary_users": "주요 사용자",
        "demo_note": "데모 메모",
        "checked_items": "검증 항목",
        "implementation_guardrails": "운영 가드레일",
        "data_readiness_question": "데이터 확인 질문",
        "initial_service_boundary": "초기 서비스 경계",
        "prd_packet": "PRD 패킷",
        "prd_quality": "PRD 품질",
        "prd_report": "PRD 보고서",
        "stage_goal": "단계 목표",
        "one_page_summary": "한 장 요약",
        "problem": "문제 정의",
        "customer_pain": "고객 불편",
        "business_impact": "사업 영향",
        "current_workaround": "현재 우회 방식",
        "success_criteria": "성공 기준",
        "personas": "사용자/이해관계자",
        "needs": "필요",
        "scope": "범위",
        "in_scope": "이번 범위",
        "out_of_scope": "제외 범위",
        "screens": "화면",
        "purpose": "목적",
        "primary_user": "주요 사용자",
        "entry_point": "진입점",
        "components": "구성요소",
        "primary_actions": "주요 액션",
        "empty_states": "빈 상태",
        "error_states": "오류 상태",
        "acceptance_criteria": "인수 기준",
        "policies": "운영 정책",
        "trigger": "발생 조건",
        "rule": "정책",
        "owner": "담당",
        "exception_handling": "예외 처리",
        "metrics": "KPI",
        "baseline": "현재 기준",
        "target": "목표 기준",
        "measurement": "측정 방식",
        "data_requirements": "데이터 요구사항",
        "field_name": "필드명",
        "source": "원천",
        "freshness": "최신성 기준",
        "quality_rule": "품질 규칙",
        "event_logs": "이벤트 로그",
        "event_name": "이벤트명",
        "properties": "속성",
        "implementation_slices": "구현 단위",
        "owner_hint": "담당 힌트",
        "decision_agenda": "회의 안건",
        "topic": "안건",
        "decision_needed": "결정 필요사항",
        "options": "선택지",
        "developer_handoff": "개발 전달사항",
        "evidence_links": "근거 링크",
        "findings": "점검 결과",
        "repair_attempted": "자동 보강 여부",
        "delay_rate": "지연률",
        "sla_compliance": "SLA 준수율",
        "courier_workload_balance": "배송원 업무 균형",
        "eta_accuracy": "ETA 정확도",
        "inquiry_reduction": "문의 감소",
        "failed_delivery_rate": "배송 실패율",
        "redelivery_rate": "재배송율",
        "operational_loss": "운영 손실",
    }
    return labels.get(value, value.replace("_", " ").title())


def stage_title(stage_id: str) -> str:
    titles = {
        "stage_1": "1단계 문제 정의",
        "stage_2": "2단계 서비스 구조",
        "stage_3": "3단계 검증",
        "stage_4": "4단계 최종 보고서",
    }
    return titles.get(stage_id, stage_id)


def stage_status(session: Dict[str, Any], stage_id: str) -> str:
    outputs = session.get("stage_outputs", {})
    approved = set(session.get("approved_stages", []))
    if stage_id in approved:
        return "승인 완료"
    if stage_id == session["current_stage"] and stage_id in outputs:
        return "승인 대기"
    if stage_id == session["current_stage"]:
        return "작업 중"
    if stage_id in outputs:
        return "생성 완료"
    return "대기"


def stage_nav_label(session: Dict[str, Any], stage_id: str) -> str:
    return f"{stage_title(stage_id)} · {stage_status(session, stage_id)}"


def ensure_selected_stage(session: Dict[str, Any]) -> str:
    selected = st.session_state.get("selected_stage_id")
    if selected not in STAGE_IDS:
        selected = session["current_stage"]
    st.session_state["selected_stage_id"] = selected
    return selected


def stage_response_for(session: Dict[str, Any], stage_id: str) -> Dict[str, Any] | None:
    transient = st.session_state.get("stage_response")
    if transient and transient.get("stage_id") == stage_id:
        return transient
    output = session.get("stage_outputs", {}).get(stage_id)
    if not output:
        return None
    return {
        "session_id": session["session_id"],
        "stage_id": stage_id,
        "status": "completed",
        "output": output,
    }


def rows_for_decisions(decisions: list[Dict[str, Any]]) -> list[Dict[str, str]]:
    return [
        {
            "결정 항목": str(item.get("item", "")),
            "상태": DECISION_STATUS_LABELS.get(
                str(item.get("status", "")),
                str(item.get("status", "")),
            ),
            "근거": str(item.get("rationale") or ""),
        }
        for item in decisions
    ]


def rows_for_risks(risks: list[Dict[str, Any]]) -> list[Dict[str, str]]:
    return [
        {
            "구분": RISK_CATEGORY_LABELS.get(
                str(item.get("category", "")),
                str(item.get("category", "")),
            ),
            "수준": SEVERITY_LABELS.get(
                str(item.get("severity", "")),
                str(item.get("severity", "")),
            ),
            "내용": str(item.get("description", "")),
            "대응": str(item.get("mitigation") or ""),
        }
        for item in risks
    ]


def rows_for_citations(citations: list[Dict[str, Any]]) -> list[Dict[str, str]]:
    return [
        {
            "자료": str(item.get("title", "")),
            "종류": str(item.get("source_type", "")),
            "위치": str(item.get("locator", "")),
            "활용": str(item.get("relevance_note", "")),
        }
        for item in citations
    ]


def has_prd_packet(packet: Dict[str, Any]) -> bool:
    return bool(
        packet
        and (
            packet.get("one_page_summary")
            or packet.get("screens")
            or packet.get("data_requirements")
        )
    )


def render_prd_quality(quality: Dict[str, Any]) -> None:
    if not quality:
        return
    status = str(quality.get("status", "needs_review"))
    score = quality.get("score", 0)
    attempted = "예" if quality.get("repair_attempted") else "아니오"
    message = f"PRD 품질 점수 {score}점 · 자동 보강 {attempted}"
    if status == "ready":
        st.success(message)
        return
    findings = quality.get("findings", [])
    st.warning(message)
    if findings:
        st.dataframe([{"보완 필요": item} for item in findings], width="stretch", hide_index=True)


def render_prd_table(title: str, rows: list[Dict[str, Any]]) -> None:
    st.markdown(f"**{title}**")
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.info(f"{title} 항목이 아직 없습니다.")


def render_prd_packet(packet: Dict[str, Any], quality: Dict[str, Any] | None = None) -> None:
    if not has_prd_packet(packet):
        st.info("PRD 패킷이 없는 이전 산출물입니다. 원본 구조화 출력을 확인하세요.")
        return

    render_prd_quality(quality or {})
    st.markdown(f"**한 장 요약**\n\n{packet.get('one_page_summary', '')}")
    render_key_values(
        {
            "stage_goal": packet.get("stage_goal", ""),
            "problem": packet.get("problem", {}),
            "personas": packet.get("personas", []),
            "scope": packet.get("scope", {}),
        }
    )


def render_prd_execution(packet: Dict[str, Any]) -> None:
    render_prd_table("화면 요구사항", packet.get("screens", []))
    render_prd_table("운영 정책", packet.get("policies", []))
    render_prd_table("KPI", packet.get("metrics", []))


def render_prd_data(packet: Dict[str, Any]) -> None:
    render_prd_table("데이터 요구사항", packet.get("data_requirements", []))
    render_prd_table("이벤트 로그", packet.get("event_logs", []))


def render_prd_handoff(packet: Dict[str, Any]) -> None:
    render_prd_table("구현 단위", packet.get("implementation_slices", []))
    handoff = packet.get("developer_handoff", [])
    if handoff:
        st.markdown("**개발 전달사항**")
        st.dataframe([{"전달사항": item} for item in handoff], width="stretch", hide_index=True)
    else:
        st.info("개발 전달사항이 아직 없습니다.")
    render_prd_table("회의 안건", packet.get("decision_agenda", []))
    render_prd_table("미확정 질문", packet.get("open_questions", []))


@st.cache_resource
def pdf_font_names() -> tuple[str, str]:
    for font_name, regular_path, bold_path in PDF_FONT_CANDIDATES:
        if Path(regular_path).exists() and Path(bold_path).exists():
            regular = f"{font_name}Regular"
            bold = f"{font_name}Bold"
            pdfmetrics.registerFont(TTFont(regular, regular_path))
            pdfmetrics.registerFont(TTFont(bold, bold_path))
            return regular, bold
    return "Helvetica", "Helvetica-Bold"


def markdown_value(value: Any, depth: int = 0) -> list[str]:
    indent = "  " * depth
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{indent}- **{format_label(str(key))}**")
                lines.extend(markdown_value(item, depth + 1))
            else:
                lines.append(f"{indent}- **{format_label(str(key))}**: {display_value(item)}")
        return lines
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.extend(markdown_value(item, depth))
            else:
                lines.append(f"{indent}- {display_value(item)}")
        return lines
    return [f"{indent}- {display_value(value)}"]


def business_heading_for_stage(stage_id: str) -> str:
    headings = {
        "stage_1": "문제 정의 및 KPI 검토",
        "stage_2": "MVP 범위 및 운영안 검토",
        "stage_3": "리스크 점검 및 보류 조건 검토",
        "stage_4": "최종 추진안 정리",
    }
    return headings.get(stage_id, stage_title(stage_id))


def prd_packet_markdown(packet: Dict[str, Any]) -> list[str]:
    lines = [
        "## 2. PRD 핵심 요약",
        packet.get("one_page_summary", ""),
        "",
        "## 3. 문제 정의",
    ]
    lines.extend(markdown_value(packet.get("problem", {})))
    lines.extend(["", "## 4. 대상 사용자 및 범위"])
    lines.extend(markdown_value({"personas": packet.get("personas", [])}))
    lines.extend(markdown_value({"scope": packet.get("scope", {})}))
    lines.extend(["", "## 5. 화면 및 운영 정책"])
    lines.extend(markdown_value({"screens": packet.get("screens", [])}))
    lines.extend(markdown_value({"policies": packet.get("policies", [])}))
    lines.extend(["", "## 6. KPI"])
    lines.extend(markdown_value(packet.get("metrics", [])))
    lines.extend(["", "## 7. 데이터 및 이벤트 로그"])
    lines.extend(markdown_value({"data_requirements": packet.get("data_requirements", [])}))
    lines.extend(markdown_value({"event_logs": packet.get("event_logs", [])}))
    lines.extend(["", "## 8. 개발 전달사항"])
    lines.extend(markdown_value({"implementation_slices": packet.get("implementation_slices", [])}))
    lines.extend(markdown_value({"developer_handoff": packet.get("developer_handoff", [])}))
    lines.extend(["", "## 9. 회의 안건 및 미확정 질문"])
    lines.extend(markdown_value({"decision_agenda": packet.get("decision_agenda", [])}))
    lines.extend(markdown_value({"open_questions": packet.get("open_questions", [])}))
    return lines


def stage_output_markdown(stage_id: str, output: Dict[str, Any]) -> str:
    packet = output.get("prd_packet", {})
    if has_prd_packet(packet):
        lines = [
            "# 업무보고",
            "",
            f"- 문서명: {business_heading_for_stage(stage_id)}",
            "- 보고 목적: 서비스 PRD 검토 및 개발 회의 안건 정리",
            "- 보고 대상: 사업/운영 의사결정권자 및 개발 리드",
            "",
            "## 1. 검토 배경",
            output.get("summary", ""),
            "",
        ]
        lines.extend(prd_packet_markdown(packet))
        risks = output.get("risks", [])
        if risks:
            lines.extend(["", "## 10. 리스크 및 대응방안"])
            lines.extend(markdown_value(risks))
        citations = output.get("citations", [])
        if citations:
            lines.extend(["", "## 11. 참고자료 및 링크"])
            lines.extend(markdown_value(citations))
        return "\n".join(str(line) for line in lines)

    lines = [
        "# 업무보고",
        "",
        f"- 문서명: {business_heading_for_stage(stage_id)}",
        "- 보고 목적: 서비스 기획 검토 및 후속 실행 방향 정리",
        "- 보고 대상: 사업/운영 의사결정권자",
        "",
        "## 1. 검토 배경",
        output.get("summary", ""),
        "",
        "## 2. 주요 검토사항",
    ]
    lines.extend(markdown_value(output.get("planner_view", {})))
    lines.extend(["", "## 3. 의사결정 필요사항"])
    lines.extend(markdown_value(output.get("decision_points", [])))
    required = output.get("required_user_input", [])
    if required:
        lines.extend(["", "## 4. 추가 확인 필요사항"])
        lines.extend(markdown_value(required))
    lines.extend(["", "## 5. 리스크 및 대응방안"])
    lines.extend(markdown_value(output.get("risks", [])))
    lines.extend(["", "## 6. 실행 전환 참고사항"])
    lines.extend(markdown_value(output.get("engineer_view", {})))
    citations = output.get("citations", [])
    if citations:
        lines.extend(["", "## 7. 참고자료 및 링크"])
        lines.extend(markdown_value(citations))
    return "\n".join(str(line) for line in lines)


def report_markdown(report: Dict[str, Any]) -> str:
    packet = report.get("prd_report", {})
    if has_prd_packet(packet):
        lines = [
            "# 최종 업무보고서",
            "",
            "- 문서명: 서비스 PRD 및 개발 착수 검토안",
            "- 보고 목적: 시연 결과 기반 추진 범위와 개발 회의 안건 확정",
            "- 보고 대상: 사업/운영 의사결정권자 및 개발 리드",
            "",
            "## 1. 종합 의견",
            packet.get("one_page_summary", ""),
            "",
        ]
        lines.extend(prd_packet_markdown(packet))
        decision_log = report.get("decision_log", [])
        if decision_log:
            lines.extend(["", "## 10. 의사결정 이력"])
            lines.extend(markdown_value(decision_log))
        risks = report.get("risks", [])
        if risks:
            lines.extend(["", "## 11. 리스크 및 대응방안"])
            lines.extend(markdown_value(risks))
        citations = report.get("citations", [])
        if citations:
            lines.extend(["", "## 12. 참고자료 및 링크"])
            lines.extend(markdown_value(citations))
        return "\n".join(str(line) for line in lines)

    lines = [
        "# 최종 업무보고서",
        "",
        "- 문서명: Milemate 서비스 기획 최종 보고",
        "- 보고 목적: 추진 여부 판단 및 후속 과제 확정",
        "- 보고 형식: 현황, 추진 방향, 리스크, 실행 계획 중심",
        "",
        "## 1. 추진 배경 및 목표",
    ]
    lines.extend(markdown_value(report.get("planner_report", {})))
    lines.extend(["", "## 2. 실행 계획 및 시스템 반영사항"])
    lines.extend(markdown_value(report.get("engineer_report", {})))
    lines.extend(["", "## 3. 의사결정 이력"])
    lines.extend(markdown_value(report.get("decision_log", [])))
    risks = report.get("risks", [])
    if risks:
        lines.extend(["", "## 4. 리스크 및 대응방안"])
        lines.extend(markdown_value(risks))
    citations = report.get("citations", [])
    if citations:
        lines.extend(["", "## 5. 참고자료 및 링크"])
        lines.extend(markdown_value(citations))
    return "\n".join(str(line) for line in lines)


def markdown_to_pdf_bytes(markdown_text: str) -> bytes:
    regular_font, bold_font = pdf_font_names()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="milemate 업무보고",
    )
    styles = {
        "title": ParagraphStyle(
            "KoreanTitle",
            fontName=bold_font,
            fontSize=18,
            leading=24,
            spaceAfter=10,
        ),
        "heading": ParagraphStyle(
            "KoreanHeading",
            fontName=bold_font,
            fontSize=12.5,
            leading=18,
            spaceBefore=8,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "KoreanBody",
            fontName=regular_font,
            fontSize=10,
            leading=15,
            spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "KoreanBullet",
            fontName=regular_font,
            fontSize=9.7,
            leading=14,
            leftIndent=8 * mm,
            firstLineIndent=-3 * mm,
            spaceAfter=3,
        ),
    }
    story = []
    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            story.append(Spacer(1, 3 * mm))
            continue
        if line.startswith("# "):
            story.append(Paragraph(escape(line[2:]), styles["title"]))
        elif line.startswith("## "):
            story.append(Paragraph(escape(line[3:]), styles["heading"]))
        elif line.startswith("- "):
            text = line[2:].replace("**", "")
            story.append(Paragraph(f"• {escape(text)}", styles["bullet"]))
        else:
            text = line.replace("**", "")
            story.append(Paragraph(escape(text), styles["body"]))

    def draw_footer(canvas, doc_obj) -> None:
        canvas.saveState()
        canvas.setFont(regular_font, 8)
        canvas.drawString(18 * mm, 10 * mm, "milemate 업무보고")
        canvas.drawRightString(192 * mm, 10 * mm, f"{doc_obj.page}쪽")
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    return buffer.getvalue()


def stage_output_pdf_bytes(stage_id: str, output: Dict[str, Any]) -> bytes:
    return markdown_to_pdf_bytes(stage_output_markdown(stage_id, output))


def report_pdf_bytes(report: Dict[str, Any]) -> bytes:
    return markdown_to_pdf_bytes(report_markdown(report))


def render_downloads(stage_id: str, output: Dict[str, Any], key_prefix: str) -> None:
    cols = st.columns(2)
    cols[0].download_button(
        "PDF 저장",
        data=stage_output_pdf_bytes(stage_id, output),
        file_name=f"milemate-{stage_id}-report.pdf",
        mime="application/pdf",
        key=f"{key_prefix}-pdf-{stage_id}",
        width="stretch",
    )
    cols[1].download_button(
        "JSON 저장",
        data=json.dumps(output, ensure_ascii=False, indent=2),
        file_name=f"milemate-{stage_id}.json",
        mime="application/json",
        key=f"{key_prefix}-json-{stage_id}",
        width="stretch",
    )


def render_verifier_banner(output: Dict[str, Any]) -> None:
    status = str(output.get("planner_view", {}).get("verifier_status", ""))
    if not status:
        return
    decision = str(output.get("planner_view", {}).get("decision", ""))
    if status == "pass":
        st.success(f"검증 통과 · {decision}")
    else:
        st.warning(f"검증 주의 · {decision}")


def render_stage_output(stage_response: Dict[str, Any]) -> None:
    output = stage_response.get("output", {})
    stage_id = stage_response.get("stage_id", "")
    packet = output.get("prd_packet", {})
    quality = output.get("prd_quality", {})
    st.subheader(f"{stage_title(stage_id)} 산출물")
    st.markdown(f"**핵심 요약**\n\n{output.get('summary', '')}")

    if stage_id == "stage_3":
        render_verifier_banner(output)

    quality_status = str(quality.get("status", ""))
    quality_label = {"ready": "충족", "needs_review": "검토 필요"}.get(
        quality_status, quality_status or "-"
    )
    metric_cols = st.columns(5)
    metric_cols[0].metric(
        "결정 항목", len(output.get("decision_points", [])), help="이번 단계에서 제안된 의사결정 수"
    )
    metric_cols[1].metric(
        "추가 요청", len(output.get("required_user_input", [])), help="사용자 확인이 필요한 항목 수"
    )
    metric_cols[2].metric("리스크", len(output.get("risks", [])), help="식별된 리스크 수")
    metric_cols[3].metric("근거 자료", len(output.get("citations", [])), help="연결된 근거 자료 수")
    metric_cols[4].metric(
        "PRD 품질", str(quality.get("score", 0)), help=f"PRD 완성도 점수 · 상태 {quality_label}"
    )

    tab_labels = [
        "PRD 요약",
        "화면/정책",
        "데이터/로그",
        "결정/리스크",
        "개발 전달",
        "근거/파일",
        "원본 출력",
    ]
    prd_tab, execution_tab, data_tab, decisions_tab, handoff_tab, evidence_tab, raw_tab = (
        st.tabs(tab_labels)
    )
    with prd_tab:
        render_prd_packet(packet, quality)
    with execution_tab:
        if has_prd_packet(packet):
            render_prd_execution(packet)
        else:
            render_key_values(output.get("planner_view", {}))
    with data_tab:
        if has_prd_packet(packet):
            render_prd_data(packet)
        else:
            render_key_values(output.get("engineer_view", {}))
    with decisions_tab:
        decisions = output.get("decision_points", [])
        if decisions:
            st.dataframe(rows_for_decisions(decisions), width="stretch", hide_index=True)
        else:
            st.info("아직 결정 항목이 없습니다.")
        required = output.get("required_user_input", [])
        if required:
            st.markdown("**추가로 필요한 입력**")
            st.dataframe([{"요청": item} for item in required], width="stretch", hide_index=True)
        risks = output.get("risks", [])
        if risks:
            st.markdown("**리스크**")
            st.dataframe(rows_for_risks(risks), width="stretch", hide_index=True)
        else:
            st.info("등록된 리스크가 없습니다.")
    with handoff_tab:
        if has_prd_packet(packet):
            render_prd_handoff(packet)
        else:
            render_key_values(output.get("engineer_view", {}))
    with evidence_tab:
        citations = output.get("citations", [])
        if citations:
            st.markdown("**근거 자료**")
            st.dataframe(rows_for_citations(citations), width="stretch", hide_index=True)
        else:
            st.info("이 산출물에 연결된 근거 자료가 없습니다.")
        render_downloads(stage_id, output, key_prefix="stage-detail")
    with raw_tab:
        st.markdown("**기획 브리프 원본**")
        render_key_values(output.get("planner_view", {}))
        st.markdown("**실행 전환본 원본**")
        render_key_values(output.get("engineer_view", {}))


def render_scenario_info(scenario_meta: Dict[str, Any]) -> None:
    description = scenario_meta.get("description", "")
    if description:
        st.caption(description)

    pain_points = scenario_meta.get("pain_points", [])
    if pain_points:
        st.markdown("**현재 문제**")
        render_list(pain_points)

    kpi_targets = scenario_meta.get("kpi_targets", {})
    if kpi_targets:
        st.markdown("**KPI 목표**")
        rows = [
            {"KPI": format_label(str(key)), "목표": str(value)}
            for key, value in kpi_targets.items()
        ]
        st.dataframe(rows, width="stretch", hide_index=True)


def render_session(session: Dict[str, Any]) -> None:
    st.caption(f"세션 {session['session_id']}")
    cols = st.columns(3)
    cols[0].metric("현재 단계", stage_title(session["current_stage"]))
    cols[1].metric("승인됨", len(session.get("approved_stages", [])))
    cols[2].metric("생성 결과", len(session.get("stage_outputs", {})))

    history = session.get("stage_history", [])
    rollback_events = session.get("rollback_events", [])
    if history or rollback_events:
        with st.expander("진행 로그", expanded=False):
            if history:
                st.markdown("**스테이지 이력**")
                st.dataframe(history, width="stretch", hide_index=True)
            if rollback_events:
                st.markdown("**롤백 기록**")
                st.dataframe(rollback_events, width="stretch", hide_index=True)


def render_stage_stepper(session: Dict[str, Any]) -> None:
    steps = []
    for idx, stage_id in enumerate(STAGE_IDS, start=1):
        status = stage_status(session, stage_id)
        icon, css_class = STAGE_STATUS_STYLE.get(status, ("⚪", "pending"))
        name = stage_title(stage_id).split(" ", 1)[-1]
        steps.append(
            f'<div class="stage-step {css_class}">'
            f'<div class="stage-dot">{icon}</div>'
            f'<div class="stage-name">{idx}. {name}</div>'
            f'<div class="stage-state">{status}</div>'
            f"</div>"
        )
    st.markdown(f'<div class="stage-stepper">{"".join(steps)}</div>', unsafe_allow_html=True)


def render_stage_navigator(session: Dict[str, Any]) -> str:
    selected = ensure_selected_stage(session)
    st.subheader("스테이지 탐색")
    render_stage_stepper(session)
    selected = st.radio(
        "열람할 스테이지",
        STAGE_IDS,
        index=STAGE_IDS.index(selected),
        format_func=lambda stage_id: stage_nav_label(session, stage_id),
        horizontal=True,
    )
    st.session_state["selected_stage_id"] = selected
    return selected


def render_stage_placeholder(session: Dict[str, Any], stage_id: str) -> None:
    with st.container(border=True):
        st.subheader(f"{stage_title(stage_id)} 산출물")
        if stage_id == session["current_stage"]:
            st.info(
                "이 단계의 산출물이 아직 없습니다. 하단 대화창의 전송 및 생성 "
                "버튼으로 생성할 수 있습니다."
            )
        else:
            st.info("아직 생성되지 않은 단계입니다. 앞 단계 승인 후 확인할 수 있습니다.")


def render_artifact_library(session: Dict[str, Any], report: Dict[str, Any] | None) -> None:
    st.subheader("산출물 보관함")
    outputs = session.get("stage_outputs", {})
    if not outputs and not report:
        st.info("생성된 산출물이 없습니다.")
        return

    for stage_id in STAGE_IDS:
        output = outputs.get(stage_id)
        if not output:
            continue
        with st.container(border=True):
            st.markdown(f"**{stage_title(stage_id)}**")
            packet_summary = output.get("prd_packet", {}).get("one_page_summary")
            st.caption(str(packet_summary or output.get("summary", ""))[:120])
            if st.button("열기", key=f"open-{session['session_id']}-{stage_id}", width="stretch"):
                st.session_state["selected_stage_id"] = stage_id
                st.rerun()
            render_downloads(stage_id, output, key_prefix=f"library-{session['session_id']}")

    if report:
        with st.container(border=True):
            st.markdown("**최종 보고서**")
            st.caption("승인된 스테이지 결과를 묶은 발표용 보고서입니다.")
            cols = st.columns(2)
            cols[0].download_button(
                "PDF 저장",
                data=report_pdf_bytes(report),
                file_name="milemate-final-report.pdf",
                mime="application/pdf",
                key=f"report-pdf-{session['session_id']}",
                width="stretch",
            )
            cols[1].download_button(
                "JSON 저장",
                data=json.dumps(report, ensure_ascii=False, indent=2),
                file_name="milemate-final-report.json",
                mime="application/json",
                key=f"report-json-{session['session_id']}",
                width="stretch",
            )


def render_report(report: Dict[str, Any]) -> None:
    st.subheader("최종 보고서")

    prd_report = report.get("prd_report", {})
    quality = report.get("prd_quality", {})
    summary_cols = st.columns(4)
    summary_cols[0].metric("결정 이력", len(report.get("decision_log", [])))
    summary_cols[1].metric("리스크", len(report.get("risks", [])))
    summary_cols[2].metric("근거 자료", len(report.get("citations", [])))
    summary_cols[3].metric("PRD 품질", str(quality.get("score", 0)))

    one_page = prd_report.get("one_page_summary")
    if one_page:
        with st.container(border=True):
            st.markdown(f"**한 장 요약**\n\n{one_page}")

    prd_tab, planner_tab, engineer_tab, log_tab = st.tabs(
        ["PRD 보고서", "업무보고 요약", "실행 계획", "결정 이력"]
    )
    with prd_tab:
        render_prd_packet(prd_report, quality)
        if has_prd_packet(prd_report):
            st.divider()
            st.markdown("##### 화면 · 정책 · KPI")
            render_prd_execution(prd_report)
            st.divider()
            st.markdown("##### 데이터 · 이벤트 로그")
            render_prd_data(prd_report)
            st.divider()
            st.markdown("##### 개발 전달 · 안건")
            render_prd_handoff(prd_report)
    with planner_tab:
        render_key_values(report.get("planner_report", {}))
    with engineer_tab:
        render_key_values(report.get("engineer_report", {}))
    with log_tab:
        decisions = report.get("decision_log", [])
        if decisions:
            st.dataframe(
                rows_for_decisions(decisions),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("기록된 결정 이력이 없습니다.")
        risks = report.get("risks", [])
        if risks:
            st.markdown("**리스크**")
            st.dataframe(rows_for_risks(risks), width="stretch", hide_index=True)


def set_error(message: str) -> None:
    st.session_state["error"] = message


def clear_error() -> None:
    st.session_state["error"] = ""


def sync_input_to_scenario() -> None:
    scenario_id = st.session_state["scenario_id"]
    st.session_state["user_input"] = scenario_title(st.session_state["demo_inputs"], scenario_id)
    st.session_state["session"] = None
    st.session_state["stage_response"] = None
    st.session_state["report"] = None
    st.session_state["stage_chats"] = {}
    st.session_state["assistant_summaries"] = set()
    st.session_state["selected_stage_id"] = "stage_1"
    clear_error()


def refresh_session(session_id: str) -> None:
    st.session_state["session"] = api_request("GET", f"/sessions/{session_id}")


def current_stage_response(session: Dict[str, Any]) -> Dict[str, Any] | None:
    return stage_response_for(session, session["current_stage"])


def build_generation_context(
    session: Dict[str, Any],
    verification_preset: str,
    demo_inputs: Dict[str, Dict[str, Any]],
    scenario_id: str,
) -> Dict[str, Any]:
    if session["current_stage"] != "stage_3":
        return {}
    return verification_context_for_preset(
        verification_preset,
        demo_inputs.get(scenario_id, {}),
    )


def stage_chat_messages(session_id: str, stage_id: str) -> list[Dict[str, str]]:
    chats = st.session_state.setdefault("stage_chats", {})
    session_chats = chats.setdefault(session_id, {})
    return session_chats.setdefault(stage_id, [])


def demo_stage_request(scenario_id: str, stage_id: str) -> str:
    scenario_requests = DEMO_STAGE_REQUESTS.get(scenario_id, {})
    return scenario_requests.get(stage_id, DEFAULT_DEMO_STAGE_REQUESTS[stage_id])


def stage_chat_draft_key(session_id: str, scenario_id: str, stage_id: str) -> str:
    return f"stage_chat_draft:{session_id}:{scenario_id}:{stage_id}"


def render_stage_chat(
    session: Dict[str, Any],
    scenario_id: str,
    base_input: str,
    context: Dict[str, Any],
) -> None:
    session_id = session["session_id"]
    stage_id = session["current_stage"]
    draft_key = stage_chat_draft_key(session_id, scenario_id, stage_id)
    if st.session_state.pop("clear_stage_chat_draft", None) == draft_key:
        st.session_state[draft_key] = ""
    elif draft_key not in st.session_state:
        st.session_state[draft_key] = demo_stage_request(scenario_id, stage_id)

    st.divider()
    st.subheader("현재 단계 대화")
    st.caption("전송된 요청은 다음 단계 생성에 반영됩니다.")
    messages = stage_chat_messages(session_id, stage_id)
    with st.container(height=360, border=True):
        if not messages:
            st.info("데모용 요청 문장이 아래 입력창에 준비되어 있습니다.")
        for message in messages:
            role = "assistant" if message["role"] == "assistant" else "user"
            with st.chat_message(role):
                st.markdown(message["content"])

    input_col, send_col = st.columns([5, 1], gap="small", vertical_alignment="bottom")
    with input_col:
        st.text_area(
            "대화 입력",
            height=122,
            key=draft_key,
            label_visibility="collapsed",
            placeholder=f"{stage_title(stage_id)}에 반영할 내용을 입력하세요",
            disabled=st.session_state.get("is_generating", False),
        )
    with send_col:
        if st.button(
            "전송 및 생성",
            type="primary",
            width="stretch",
            disabled=st.session_state.get("is_generating", False),
        ):
            prompt = str(st.session_state.get(draft_key, "")).strip()
            if not prompt:
                set_error("전송할 요청을 입력하세요.")
                return
            clear_error()
            messages.append({"role": "user", "content": prompt})
            st.session_state["clear_stage_chat_draft"] = draft_key
            start_stage_generation(session, base_input, context)


def build_stage_user_input(session: Dict[str, Any], base_input: str) -> str:
    messages = stage_chat_messages(session["session_id"], session["current_stage"])
    user_messages = [item["content"] for item in messages if item["role"] == "user"]
    parts = [
        "초기 사용자 설명:",
        base_input.strip() or "(없음)",
    ]
    if user_messages:
        parts.extend(
            [
                "",
                "사용자의 추가 요청은 개발 지시가 아니라 서비스 기획 관점의 문장입니다. "
                "수요, 공급, 비용, 마케팅, 운영 기획 의도를 해석해 개발 관점 출력으로 변환하세요.",
                "",
                f"{stage_title(session['current_stage'])} 대화에서 사용자가 추가한 "
                "서비스 기획 요청:",
            ]
        )
        parts.extend(f"- {message}" for message in user_messages)
    return "\n".join(parts)


def append_generation_summary(session_id: str, stage_id: str, summary: str) -> None:
    key = f"{session_id}:{stage_id}"
    seen = st.session_state.setdefault("assistant_summaries", set())
    if key in seen:
        return
    stage_chat_messages(session_id, stage_id).append(
        {"role": "assistant", "content": f"생성 완료: {summary}"}
    )
    seen.add(key)


@st.cache_data(show_spinner=False)
def loading_cat_sprite_data_uri(path: str) -> str:
    asset_path = Path(path)
    if not asset_path.exists():
        return ""
    encoded = base64.b64encode(asset_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def generation_visual_markup() -> str:
    sprite_uri = loading_cat_sprite_data_uri(str(LOADING_CAT_SPRITE_PATH))
    if not sprite_uri:
        return '<div class="generation-orbit"></div>'
    return (
        '<div class="generation-cat-sprite" '
        f'style="background-image: url({sprite_uri});" '
        'aria-label="고양이가 털실 공을 굴리는 생성 중 애니메이션"></div>'
    )


def start_stage_generation(
    session: Dict[str, Any],
    base_input: str,
    context: Dict[str, Any],
) -> None:
    st.session_state["pending_stage_run"] = {
        "session_id": session["session_id"],
        "stage_id": session["current_stage"],
        "user_input": build_stage_user_input(session, base_input),
        "context": context,
        "started_at": time.time(),
    }
    st.session_state["is_generating"] = True
    st.rerun()


def run_pending_stage_generation() -> None:
    pending = st.session_state.get("pending_stage_run")
    if not pending:
        return
    stage_id = pending["stage_id"]
    started_at = pending.get("started_at", time.time())
    st.markdown(
        f"""
        <div class="generation-overlay">
          <div class="generation-panel">
            {generation_visual_markup()}
            <div class="generation-title">
              {stage_title(stage_id)} 생성 중&hellip;
            </div>
            <div class="generation-copy">
              웹 검색으로 외부 자료를 확인하고<br>
              근거 링크를 포함한 한국어 결과를 구성하고 있습니다.
            </div>
            <div class="generation-dots"><span></span><span></span><span></span></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.status(f"{stage_title(stage_id)} 생성 중", expanded=True) as status:
        st.write("Codex CLI 호출 준비")
        st.write("외부 자료 웹 검색")
        st.write("Structured output schema 검증")
        st.write(f"경과 시간: {time.time() - started_at:.1f}초")
        try:
            response = api_request(
                "POST",
                "/stages/run",
                {
                    "session_id": pending["session_id"],
                    "user_input": pending["user_input"],
                    "context": pending["context"],
                },
            )
            st.session_state["stage_response"] = response
            refresh_session(pending["session_id"])
            st.session_state["report"] = None
            st.session_state["selected_stage_id"] = stage_id
            append_generation_summary(
                pending["session_id"],
                stage_id,
                response.get("output", {}).get("summary", ""),
            )
            status.update(label=f"{stage_title(stage_id)} 생성 완료", state="complete")
        except RuntimeError as exc:
            status.update(label=f"{stage_title(stage_id)} 생성 실패", state="error")
            set_error(str(exc))
        finally:
            st.session_state["pending_stage_run"] = None
            st.session_state["is_generating"] = False
            st.rerun()


st.set_page_config(page_title="milemate", layout="wide")
st.markdown(
    """
    <style>
    /* ── 색상 토큰 ───────────────────────────────────────────────────────── */
    :root {
      --brand:        #0f766e;   /* teal-700  — 주 액션·강조 */
      --brand-mid:    #14b8a6;   /* teal-500  — 호버·보조 액션 */
      --brand-light:  #ccfbf1;   /* teal-100  — 연한 강조 배경 */
      --brand-bg:     #f0fdfa;   /* teal-50   — 섹션 배경 */
      --brand-dark:   #134e4a;   /* teal-900  — 헤더·진한 텍스트 */
      --done:         #15803d;   /* green-700 — 승인 완료 */
      --done-bg:      #dcfce7;   /* green-100 */
      --warn:         #b45309;   /* amber-700 — 검토 대기 */
      --warn-bg:      #fef9c3;   /* amber-100 */
      --text:         #0f172a;   /* slate-900 */
      --text-muted:   #475569;   /* slate-600 */
      --surface:      #f8fafc;   /* slate-50  */
      --border:       #e2e8f0;   /* slate-200 */
      --border-brand: #99f6e4;   /* teal-200  */
    }

    /* ── 레이아웃 ────────────────────────────────────────────────────────── */
    .block-container { max-width: 1180px; padding-top: 1rem; }

    /* ── 페이지 타이틀 ───────────────────────────────────────────────────── */
    h1:first-of-type {
      color: var(--brand-dark);
      border-bottom: 3px solid var(--brand);
      padding-bottom: 8px;
      margin-bottom: 16px;
    }

    /* ── 메트릭 카드 ─────────────────────────────────────────────────────── */
    div[data-testid="stMetric"] {
      border: 1px solid var(--border);
      border-top: 3px solid var(--brand);
      background: var(--brand-bg);
      padding: 10px 12px;
      border-radius: 8px;
    }
    div[data-testid="stMetric"] label { color: var(--text-muted); }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
      color: var(--brand-dark);
      font-weight: 700;
    }

    /* ── 사이드바 ────────────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {
      background: var(--brand-bg);
      border-right: 1px solid var(--border-brand);
    }
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] label { color: var(--brand-dark) !important; }

    /* ── 탭 ──────────────────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 2px solid var(--border); }
    .stTabs [data-baseweb="tab"] {
      color: var(--text-muted);
      border-radius: 6px 6px 0 0;
    }
    .stTabs [aria-selected="true"] {
      color: var(--brand) !important;
      border-bottom: 2px solid var(--brand) !important;
      font-weight: 600;
    }

    /* ── 컨테이너 (border=True) ──────────────────────────────────────────── */
    [data-testid="stVerticalBlockBorderWrapper"] > div {
      border-color: var(--border-brand) !important;
      border-radius: 10px !important;
    }

    /* ── 버튼 ────────────────────────────────────────────────────────────── */
    .stButton > button[kind="primary"] {
      background: var(--brand);
      border: none;
      color: #fff;
    }
    .stButton > button[kind="primary"]:hover {
      background: var(--brand-mid);
    }
    .stButton > button:not([kind="primary"]) {
      border-color: var(--border-brand);
      color: var(--brand-dark);
    }
    .stButton > button:not([kind="primary"]):hover {
      background: var(--brand-bg);
      border-color: var(--brand);
    }

    /* ── 다운로드 버튼 ───────────────────────────────────────────────────── */
    .stDownloadButton > button {
      border-color: var(--border-brand);
      color: var(--brand-dark);
    }
    .stDownloadButton > button:hover {
      background: var(--brand-bg);
      border-color: var(--brand);
    }

    /* ── 알림/배너 ───────────────────────────────────────────────────────── */
    [data-testid="stInfo"] {
      background: var(--brand-bg);
      border-left-color: var(--brand) !important;
      color: var(--brand-dark);
    }

    /* ── 스테이지 스테퍼 ─────────────────────────────────────────────────── */
    .stage-stepper {
      display: flex;
      align-items: stretch;
      gap: 0;
      margin: 6px 0 18px;
      padding: 16px 20px;
      background: var(--brand-bg);
      border: 1px solid var(--border-brand);
      border-radius: 14px;
    }
    .stage-step {
      flex: 1 1 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      position: relative;
      padding: 0 6px;
    }
    .stage-step .stage-dot {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      border: 2px solid var(--border);
      background: #ffffff;
      z-index: 1;
    }
    .stage-step .stage-name {
      font-size: 0.84rem;
      font-weight: 600;
      color: var(--text);
      margin-top: 7px;
    }
    .stage-step .stage-state {
      font-size: 0.72rem;
      color: var(--text-muted);
      margin-top: 2px;
    }
    .stage-step::before, .stage-step::after {
      content: "";
      position: absolute;
      top: 18px;
      height: 2px;
      background: var(--border);
      width: 50%;
      z-index: 0;
    }
    .stage-step::before { left: 0; }
    .stage-step::after  { right: 0; }
    .stage-step:first-child::before { display: none; }
    .stage-step:last-child::after   { display: none; }
    /* 상태별 dot 색 */
    .stage-step.done .stage-dot {
      border-color: var(--done); background: var(--done); color: #fff;
    }
    .stage-step.done .stage-name  { color: var(--done); }
    .stage-step.review .stage-dot {
      border-color: var(--warn); background: var(--warn-bg);
    }
    .stage-step.review .stage-name { color: var(--warn); }
    .stage-step.active .stage-dot {
      border-color: var(--brand); background: var(--brand-light);
    }
    .stage-step.active .stage-name { color: var(--brand); }
    .stage-step.generated .stage-dot {
      border-color: var(--border-brand); background: var(--brand-bg);
    }
    /* 커넥터 선 */
    .stage-step.done::before, .stage-step.done::after { background: var(--done); }
    .stage-step.review::before { background: var(--done); }
    .stage-step.active::before { background: var(--brand); }

    /* ── 생성 오버레이 ───────────────────────────────────────────────────── */
    .generation-overlay {
      position: fixed;
      inset: 0;
      z-index: 9999;
      background: rgba(19, 78, 74, 0.65);
      backdrop-filter: blur(5px);
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .generation-panel {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 20px;
      background: #ffffff;
      border-top: 4px solid var(--brand);
      border-radius: 24px;
      padding: 44px 52px 36px;
      width: min(480px, 90vw);
      box-shadow: 0 32px 80px rgba(15, 118, 110, 0.25);
      text-align: center;
    }
    .generation-title {
      font-size: 1.22rem;
      font-weight: 700;
      color: var(--brand-dark);
      letter-spacing: -0.01em;
    }
    .generation-copy {
      color: var(--text-muted);
      font-size: 0.93rem;
      line-height: 1.55;
      margin-top: -6px;
    }
    .generation-orbit {
      width: 64px;
      height: 64px;
      border: 5px solid var(--brand-light);
      border-top-color: var(--brand);
      border-radius: 50%;
      animation: spin 0.9s linear infinite;
    }
    .generation-cat-sprite {
      width: 220px;
      height: 220px;
      background-color: #ffffff;
      background-repeat: no-repeat;
      background-size: 400% 200%;
      background-position: 0% 0%;
      border-radius: 20px;
      box-shadow: 0 8px 28px rgba(15, 118, 110, 0.22);
      animation: catYarnFrames 1.35s steps(1) infinite;
      mix-blend-mode: multiply;
    }
    .generation-dots {
      display: flex;
      gap: 6px;
      justify-content: center;
    }
    .generation-dots span {
      display: inline-block;
      width: 8px;
      height: 8px;
      background: var(--brand);
      border-radius: 50%;
      animation: pulse 1.2s ease-in-out infinite;
    }
    .generation-dots span:nth-child(2) { animation-delay: 0.18s; }
    .generation-dots span:nth-child(3) { animation-delay: 0.36s; }

    /* ── 키프레임 ────────────────────────────────────────────────────────── */
    @keyframes spin { to { transform: rotate(360deg); } }
    @keyframes catYarnFrames {
      0%,   12.49% { background-position: 0%      0%; }
      12.5%, 24.99% { background-position: 33.333% 0%; }
      25%,  37.49% { background-position: 66.666% 0%; }
      37.5%, 49.99% { background-position: 100%    0%; }
      50%,  62.49% { background-position: 0%      100%; }
      62.5%, 74.99% { background-position: 33.333% 100%; }
      75%,  87.49% { background-position: 66.666% 100%; }
      87.5%, 100%  { background-position: 100%    100%; }
    }
    @keyframes pulse {
      0%, 80%, 100% { opacity: 0.22; transform: translateY(0); }
      40%           { opacity: 1;    transform: translateY(-4px); }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("milemate")

scenarios = load_scenarios()
demo_inputs = load_demo_input_map()
default_scenario = (
    "dispatch_recommendation"
    if "dispatch_recommendation" in scenarios
    else next(iter(scenarios))
)

if "demo_inputs" not in st.session_state:
    st.session_state["demo_inputs"] = demo_inputs
if "scenario_id" not in st.session_state:
    st.session_state["scenario_id"] = default_scenario
if "user_input" not in st.session_state:
    st.session_state["user_input"] = scenario_title(demo_inputs, default_scenario)
if "session" not in st.session_state:
    st.session_state["session"] = None
if "stage_response" not in st.session_state:
    st.session_state["stage_response"] = None
if "report" not in st.session_state:
    st.session_state["report"] = None
if "error" not in st.session_state:
    st.session_state["error"] = ""
if "stage_chats" not in st.session_state:
    st.session_state["stage_chats"] = {}
if "assistant_summaries" not in st.session_state:
    st.session_state["assistant_summaries"] = set()
if "pending_stage_run" not in st.session_state:
    st.session_state["pending_stage_run"] = None
if "is_generating" not in st.session_state:
    st.session_state["is_generating"] = False
if "selected_stage_id" not in st.session_state:
    st.session_state["selected_stage_id"] = "stage_1"

with st.sidebar:
    scenario_id = st.selectbox(
        "시나리오",
        options=list(scenarios),
        format_func=lambda key: scenarios[key].get("label_ko") or scenarios[key]["label"],
        key="scenario_id",
        on_change=sync_input_to_scenario,
    )
    with st.expander("시나리오 개요", expanded=False):
        render_scenario_info(scenarios[scenario_id])
    user_input = st.text_area(
        "초기 설명",
        height=92,
        key="user_input",
    )
    verification_preset = st.selectbox(
        "3단계 검증 조건",
        options=list(VERIFICATION_PRESETS),
        key="verification_preset",
    )
    if st.button("세션 시작", type="primary", width="stretch"):
        try:
            clear_error()
            st.session_state["session"] = api_request(
                "POST",
                "/sessions",
                {"scenario": scenario_id, "user_input": user_input},
            )
            st.session_state["stage_response"] = None
            st.session_state["report"] = None
            st.session_state["stage_chats"] = {}
            st.session_state["assistant_summaries"] = set()
            st.session_state["pending_stage_run"] = None
            st.session_state["is_generating"] = False
            st.session_state["selected_stage_id"] = st.session_state["session"]["current_stage"]
        except RuntimeError as exc:
            set_error(str(exc))

    st.divider()
    st.caption("로컬 데모 백엔드" if API_MODE == "local" else f"백엔드 {API_BASE_URL}")

if st.session_state["error"]:
    st.error(st.session_state["error"])

session = st.session_state["session"]
if not session:
    st.info("왼쪽 사이드바에서 세션을 시작하세요.")
    st.stop()

if (
    st.session_state["stage_response"]
    and st.session_state["stage_response"].get("stage_id") != session["current_stage"]
):
    st.session_state["stage_response"] = None

render_session(session)

if st.session_state.get("pending_stage_run"):
    run_pending_stage_generation()
    st.stop()

selected_stage_id = render_stage_navigator(session)

is_generating = st.session_state.get("is_generating", False)
generation_context = build_generation_context(
    session=session,
    verification_preset=verification_preset,
    demo_inputs=demo_inputs,
    scenario_id=scenario_id,
)
action_cols = st.columns([1, 1, 3])

with action_cols[0]:
    can_approve = session["current_stage"] in session.get("stage_outputs", {})
    if st.button(
        "승인 / 다음",
        width="stretch",
        disabled=not can_approve or is_generating,
    ):
        try:
            clear_error()
            previous_stage = session["current_stage"]
            st.session_state["session"] = api_request(
                "POST",
                "/stages/approve",
                {"session_id": session["session_id"]},
            )
            st.session_state["stage_response"] = None
            st.session_state["selected_stage_id"] = st.session_state["session"][
                "current_stage"
            ]
            if previous_stage == "stage_4":
                st.session_state["report"] = api_request(
                    "GET",
                    f"/reports/{session['session_id']}",
                )
            st.rerun()
        except RuntimeError as exc:
            set_error(str(exc))

with action_cols[1]:
    if st.button("새로고침", width="stretch", disabled=is_generating):
        try:
            clear_error()
            refresh_session(session["session_id"])
            st.session_state["stage_response"] = None
            st.rerun()
        except RuntimeError as exc:
            set_error(str(exc))

current_response = current_stage_response(session)
rollback_targets = []
if current_response:
    rollback_targets = current_response.get("output", {}).get("rollback_targets", [])

if rollback_targets:
    with action_cols[2]:
        rollback_cols = st.columns([1, 2, 1])
        target = rollback_cols[0].selectbox(
            "롤백 대상",
            rollback_targets,
            label_visibility="collapsed",
            disabled=is_generating,
        )
        reason = rollback_cols[1].text_input(
            "롤백 사유",
            "범위/데이터 리스크",
            label_visibility="collapsed",
            disabled=is_generating,
        )
        if rollback_cols[2].button("롤백", width="stretch", disabled=is_generating):
            try:
                clear_error()
                st.session_state["session"] = api_request(
                    "POST",
                    "/stages/rollback",
                    {
                        "session_id": session["session_id"],
                        "target_stage": target,
                        "reason": reason,
                    },
                )
                st.session_state["stage_response"] = None
                st.session_state["report"] = None
                st.session_state["selected_stage_id"] = st.session_state["session"][
                    "current_stage"
                ]
                st.rerun()
            except RuntimeError as exc:
                set_error(str(exc))

selected_stage_response = stage_response_for(session, selected_stage_id)
workspace_cols = st.columns([2.2, 1], gap="large")
with workspace_cols[0]:
    if selected_stage_response:
        render_stage_output(selected_stage_response)
    else:
        render_stage_placeholder(session, selected_stage_id)

    if st.session_state["report"]:
        render_report(st.session_state["report"])

with workspace_cols[1]:
    render_artifact_library(session, st.session_state["report"])

render_stage_chat(session, scenario_id, user_input, generation_context)
