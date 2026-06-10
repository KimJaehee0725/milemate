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
    scenario_brief,
    scenario_display_title,
    scenario_initial_input,
    verification_context_for_preset,
)

API_BASE_URL = os.getenv("MILEMATE_API_BASE", "http://127.0.0.1:8000").rstrip("/")
API_MODE = os.getenv("MILEMATE_API_MODE", "http")
API_TIMEOUT_SECONDS = float(os.getenv("MILEMATE_API_TIMEOUT_SECONDS", "620"))
STATUS_TIMEOUT_SECONDS = float(os.getenv("MILEMATE_STATUS_TIMEOUT_SECONDS", "1.5"))
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
VERIFICATION_PRESET_LABELS = {
    "Configured evidence": "기본 자료 충분",
    "Missing data": "데이터 부족",
    "Poor labels": "품질 낮은 데이터",
}
ROLLBACK_REASON_PLACEHOLDER = """발견한 문제:
-

잘못된 가정:
-

되돌아가 수정할 내용:
-

다음 단계에서 유지할 내용:
-"""
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
        "서비스 기획안처럼 설명할 수 있게 정리해주세요. 어떤 "
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
    "rider_onboarding_dropout": {
        "stage_1": (
            "지금 우리한테는 누가 그만두기 직전인지 알아채는 것도, 먼저 연락하는 절차도 "
            "아예 없습니다. 어렵게 모집한 신규 기사 10명 중 6명이 첫 2주를 못 넘기고 "
            "조용히 사라지는데, 첫 픽업에서 헤매고 첫 콜을 못 잡고 정산이 깜깜한 그 "
            "막히는 순간을 운영팀이 미리 볼 수 있게 문제를 잡아주세요. 모집 광고비가 "
            "어디서 새는지, 첫 2주 잔존율과 첫 콜까지 걸리는 시간을 같이 보고 싶습니다."
        ),
        "stage_2": (
            "이번 MVP에서는 첫 2주에 막혀 이탈 위험이 높은 신규 기사를 매니저가 큐에서 "
            "먼저 보고, 어디서 막혔는지와 권장 연락 멘트를 확인한 뒤 직접 연락하거나 "
            "보류하는 흐름까지만 보여주고 싶습니다. 기사님께 자동으로 전화·문자가 "
            "나가는 건 아직 부담스럽고, 매니저가 하루에 감당할 수 있는 연락량과 부담 "
            "없는 멘트가 먼저 필요합니다. 잔존율과 첫 콜 완료 시간을 같이 볼 수 있게 "
            "범위를 잡아주세요."
        ),
        "stage_3": (
            "가입한 지 얼마 안 된 기사님은 활동 데이터가 거의 없어서 위험한지 판단이 "
            "어려울 것 같고, 위험하다고 너무 많이 띄우면 매니저 연락 업무가 감당 안 될 "
            "것 같습니다. 반대로 적게 띄우면 그대로 또 조용히 사라집니다. 연락 동의나 "
            "거부 의사, 개인정보 민감도까지 포함해서 어떤 경우에 연락을 줄이거나 "
            "보류해야 하는지, 데이터가 부족하면 어떤 판단을 멈춰야 하는지 점검해주세요."
        ),
        "stage_4": (
            "최종 설명은 광고비 쓰고도 조용히 사라지던 신규 기사를, 막히는 순간 "
            "운영팀이 먼저 알아채 손 내밀어 남게 만드는 새 서비스로 보이면 좋겠습니다. "
            "첫 2주 잔존율과 첫 콜 소요 시간이 어떻게 좋아지는지, 매니저는 무엇을 새로 "
            "하고, 개발팀에는 어떤 데이터를 달라고 해야 하는지 한 흐름으로 정리해주세요."
        ),
    },
    "return_pickup_flow": {
        "stage_1": (
            "고객이 종일 기다리는 것과 기사님 헛걸음, 둘 중 뭐가 더 급한 문제인지 성공 "
            "기준에 숫자로 박아주세요. 환불이 늦는다는 문의도 결국 같은 문제에서 오는 게 "
            "맞는지도 정리해주시고요."
        ),
        "stage_2": (
            "고객이 시간 고르는 화면이랑 어디까지 왔나 보는 화면, 딱 두 개면 되는 거 "
            "아닌가요? 기사님용 앱까지 이번에 다 만들어야 하는 건지 첫 버전 범위를 좀 "
            "잘라주세요."
        ),
        "stage_3": (
            "예약을 너무 많이 받아서 기사님이 다 못 도는 상황이 제일 무서운데, 그건 "
            "어디서 어떻게 막는 건가요? 고객 주소랑 연락처 다루는 것도 문제 소지가 "
            "없는지 같이 봐주세요."
        ),
        "stage_4": (
            "다음 주에 개발팀 미팅이 잡혔는데, 이게 몇 명이 얼마나 걸릴 일인지 가늠할 "
            "수 있게 제가 개발팀에 물어봐야 할 질문 목록부터 정리해주세요."
        ),
    },
    "checkout_fee_transparency": {
        "stage_1": (
            "결제 마지막에 금액이 갑자기 올라서 나가는 그 이탈 장면이랑, '예상이랑 "
            "다르다'는 문의가 얼마나 반복되는지를 성공 기준에 더 또렷하게 넣어 주세요. "
            "지금은 이런 사전 안내 화면이 아예 없다는 점도 분명히 적어 주시고요."
        ),
        "stage_2": (
            "처음엔 주소 넣으면 배송비가 왜 이 금액인지 풀어주는 안내 카드 한 화면이면 "
            "충분할 것 같아요. 거리·시간대·할증을 항목으로 쪼개서 보여주는 것까지가 1차 "
            "범위고, 정책을 바꾸거나 할인 자동으로 주는 건 빼 주세요."
        ),
        "stage_3": (
            "제일 무서운 게 미리 보여준 금액이랑 실제 결제가 다를 때예요. 그 차이가 "
            "얼마 이상이면 아예 단일 금액 말고 범위로만 보여주거나 노출을 멈추는 식으로, "
            "어떤 조건이면 보류해야 하는지 기준을 짚어 주세요."
        ),
        "stage_4": (
            "개발팀한테 '예상 금액 계산을 결제랑 똑같은 로직으로 돌릴 수 있냐', "
            "'예상가랑 실제가 차이는 어디서 잡아서 로그로 남기냐'를 물어볼 수 있게 최종 "
            "보고서랑 개발 질문지를 정리해 주세요."
        ),
    },
    "merchant_prep_visibility": {
        "stage_1": (
            "기사가 가게 앞에서 헛대기하는 게 진짜 문제라는 걸 윗선에 보여줘야 해요. "
            "대기시간이랑 매장 기인 지연이 숫자로 얼마나 되는지, 성공하면 뭐가 "
            "좋아지는지 좀 더 또렷하게 채워 주세요."
        ),
        "stage_2": (
            "기존 매장 주문 화면에 뭘 더하는 건지가 핵심이에요. 신규 주문 목록은 그대로 "
            "두고 준비현황이랑 이건 15분 걸려요 버튼이 어디에 붙는지, 기사 도착 표시까지 "
            "화면을 좀 더 구체적으로 그려 주세요."
        ),
        "stage_3": (
            "사장님들이 감시받는다고 들고일어나는 게 제일 무서워요. 평소보다 느림 신호가 "
            "부당하게 뜰 위험이랑, 매장 표본이 적을 때 어떤 조건이면 신호를 잠깐 멈춰야 "
            "하는지 보류 기준을 정리해 주세요."
        ),
        "stage_4": (
            "개발팀 회의에 그대로 들고 갈 수 있게 정리해 주세요. 매장 화면이랑 기사 "
            "쪽이 어떻게 연결되는지, 어디까지 자동이고 배차 확정은 누가 쥐는지, "
            "개발팀에 물어볼 질문지를 빠짐없이 넣어 주세요."
        ),
    },
    "cs_repeat_inquiry_triage": {
        "stage_1": (
            "문의 70%가 반복 질문이라는 게 진짜인지, 그래서 환불·분쟁이 얼마나 밀리는지 "
            "숫자로 더 분명히 잡아주세요. 성공 기준도 자동 처리율이랑 긴급 응대 시간 둘 "
            "다로요."
        ),
        "stage_2": (
            "상담사가 보는 화면에 이 문의가 왜 이렇게 분류됐는지랑 주문정보가 같이 떠야 "
            "해요. 자동으로 답하는 질문 종류랑 무조건 상담사한테 넘기는 질문을 표로 나눠 "
            "정리해 주세요."
        ),
        "stage_3": (
            "잘못 분류해서 엉뚱하게 답하거나 화난 고객한테 로봇처럼 구는 상황이 제일 "
            "걱정이에요. 분류 신뢰도가 낮으면 어떻게 멈추는지, 개인정보 연락처 답하는 게 "
            "법적으로 괜찮은지 보류 조건으로 짚어주세요."
        ),
        "stage_4": (
            "경영진 보고용으로 자동/상담사 경계랑 기대 효과를 한 장으로 정리하고, "
            "개발팀한테 던질 질문(우리 주문 조회 API랑 어떻게 붙는지, 분류 모델은 뭘 "
            "쓰는지)도 질문지로 만들어 주세요."
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


def api_binary_request(method: str, path: str) -> bytes:
    if API_MODE == "local":
        return local_demo_api().binary_request(method=method, path=path)

    req = request.Request(f"{API_BASE_URL}{path}", method=method)
    try:
        with request.urlopen(req, timeout=API_TIMEOUT_SECONDS) as response:
            return response.read()
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


@st.cache_data(ttl=5, show_spinner=False)
def fetch_runtime_status() -> Dict[str, Any]:
    if API_MODE == "local":
        return {
            "available": True,
            "mode": "local",
            "label": "로컬 리허설 모드",
            "detail": "라이브 호출 없이 기획서 작성 흐름만 점검합니다.",
            "runtime": "LocalDemoAPI",
        }

    status_url = f"{API_BASE_URL}/runtime/status"
    req = request.Request(status_url, method="GET", headers={"Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=STATUS_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
            payload = json.loads(body) if body else {}
    except (error.HTTPError, error.URLError, TimeoutError, OSError) as exc:
        return {
            "available": False,
            "mode": "http",
            "label": "라이브 Codex 연결 확인 필요",
            "detail": f"상태 확인 실패: {exc}",
            "runtime": API_BASE_URL,
        }

    if not isinstance(payload, dict):
        payload = {}
    runtime_mode = str(payload.get("runtime_mode") or "live_codex_cli")
    model_id = str(payload.get("model_id") or "")
    reasoning_effort = str(payload.get("reasoning_effort") or "")
    engine = str(payload.get("serving_engine") or "")
    cli_binary = str(payload.get("cli_binary") or "codex")
    cli_available = bool(payload.get("cli_available"))
    timeout = payload.get("timeout")
    label = "라이브 Codex 연결됨" if cli_available else "라이브 Codex 연결 확인 필요"
    detail_parts = [
        part
        for part in [
            model_id,
            f"effort {reasoning_effort}" if reasoning_effort else "",
            engine,
            f"{timeout}s timeout" if timeout else "",
        ]
        if part
    ]
    detail = " / ".join(detail_parts) or "백엔드 runtime 상태를 확인했습니다."
    return {
        "available": True,
        "mode": runtime_mode,
        "label": label,
        "detail": detail,
        "runtime": f"{cli_binary}: {'ready' if cli_available else 'not found'}",
        "raw": payload,
    }


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


def render_runtime_badge(status: Dict[str, Any]) -> None:
    mode = str(status.get("mode") or API_MODE)
    available = bool(status.get("available"))
    label = str(status.get("label") or "runtime 상태")
    detail = str(status.get("detail") or "")
    runtime = str(status.get("runtime") or "")
    raw = status.get("raw", {}) if isinstance(status.get("raw"), dict) else {}
    cli_ready = bool(raw.get("cli_available", available))
    tone = "local" if mode == "local" else "live" if available and cli_ready else "warning"
    st.markdown(
        f"""
        <div class="runtime-badge runtime-{tone}">
          <div class="runtime-kicker">실행 상태</div>
          <div class="runtime-label">{escape(label)}</div>
          <div class="runtime-detail">{escape(detail)}</div>
          <div class="runtime-endpoint">{escape(runtime)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_product_intro() -> None:
    st.markdown(
        """
        <div class="product-intro">
          <div class="product-kicker">비개발 기획자를 위한 기술기획서 작성 보조</div>
          <div class="product-copy">
            자연어 아이디어를 문제 정의, KPI, MVP 범위, 기술·데이터·규제 리스크,
            최종 기획서와 개발팀 확인사항으로 단계별 구조화합니다.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_demo_brief_block(brief: Dict[str, Any], compact: bool = False) -> None:
    title = str(brief.get("title") or "예시 브리프")
    subtitle = str(brief.get("subtitle") or "")
    summary = str(brief.get("summary") or "")
    presentation_goal = str(brief.get("presentation_goal") or "")
    decision_focus = [str(item) for item in brief.get("decision_focus", [])]
    demo_highlights = [str(item) for item in brief.get("demo_highlights", [])]
    sidebar_note = str(brief.get("sidebar_note") or "")

    if compact:
        st.markdown("### 적용 예시 브리프")
        st.markdown(f"**{title}**")
        if subtitle:
            st.caption(subtitle)
        if sidebar_note:
            st.write(sidebar_note)
        elif summary:
            st.write(summary)
        if decision_focus:
            st.markdown("**오늘 확인할 결정**")
            render_list(decision_focus[:3])
        return

    st.markdown(
        f"""
        <div class="demo-brief">
          <div class="demo-kicker">아이디어 → 기술 기획서 변환</div>
          <h2>{escape(title)}</h2>
          <p class="demo-subtitle">{escape(subtitle)}</p>
          <p>{escape(summary)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if presentation_goal:
        st.markdown(f"**검토 목표**  \n{presentation_goal}")
    cols = st.columns(2)
    with cols[0]:
        st.markdown("**오늘 확인할 결정**")
        render_list(decision_focus)
    with cols[1]:
        st.markdown("**핵심 포인트**")
        render_list(demo_highlights)


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
        "demo_note": "작업 메모",
        "checked_items": "검증 항목",
        "implementation_guardrails": "운영 가드레일",
        "data_readiness_question": "데이터 확인 질문",
        "initial_service_boundary": "초기 서비스 경계",
        "prd_packet": "기획서 패킷",
        "prd_quality": "기획서 품질",
        "prd_report": "기획서 보고서",
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
        "implementation_slices": "구현 검토 단위",
        "owner_hint": "담당 힌트",
        "decision_agenda": "회의 안건",
        "topic": "안건",
        "decision_needed": "결정 필요사항",
        "options": "선택지",
        "developer_handoff": "개발팀 확인사항",
        "evidence_links": "근거 링크",
        "findings": "점검 결과",
        "repair_attempted": "자동 보강 여부",
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
        "status": stage_history_entry(session, stage_id).get("status", "completed"),
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


def safe_count(value: Any, fallback: Any = 0) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        return len(value)
    if value is None:
        value = fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def as_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if value:
        return [str(value)]
    return []


def stage_history_entry(session: Dict[str, Any], stage_id: str) -> Dict[str, Any]:
    entries = [
        item
        for item in session.get("stage_history", [])
        if isinstance(item, dict) and item.get("stage_id") == stage_id
    ]
    return entries[-1] if entries else {}


def stage_review_state(
    session: Dict[str, Any],
    stage_id: str,
    output: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    output = output or session.get("stage_outputs", {}).get(stage_id, {}) or {}
    if not output:
        return {
            "status": "pending",
            "summary": "",
            "prd_quality_score": 0,
            "required_user_input_count": 0,
            "risk_count": 0,
            "rollback_targets": [],
        }
    history = stage_history_entry(session, stage_id)
    quality = output.get("prd_quality", {}) if isinstance(output.get("prd_quality"), dict) else {}
    rollback_targets = as_string_list(output.get("rollback_targets"))
    if not rollback_targets:
        rollback_targets = as_string_list(history.get("rollback_targets"))
    status = history.get("status")
    if not status:
        status = "completed" if output else "pending"
    return {
        "status": str(status),
        "summary": str(history.get("summary") or output.get("summary") or ""),
        "prd_quality_score": safe_count(
            quality.get("score"),
            history.get("prd_quality_score"),
        ),
        "required_user_input_count": safe_count(
            output.get("required_user_input"),
            history.get("required_user_input_count"),
        ),
        "risk_count": safe_count(output.get("risks"), history.get("risk_count")),
        "rollback_targets": rollback_targets,
    }


def rows_for_stage_history(session: Dict[str, Any]) -> list[Dict[str, Any]]:
    rows: list[Dict[str, Any]] = []
    for item in session.get("stage_history", []):
        if not isinstance(item, dict):
            continue
        stage_id = str(item.get("stage_id") or "")
        review = stage_review_state(session, stage_id)
        rows.append(
            {
                "단계": stage_title(stage_id),
                "상태": str(item.get("status") or review.get("status") or ""),
                "완료": "예" if item.get("completed") else "아니오",
                "승인": "예" if item.get("approved") else "아니오",
                "추가 입력": review.get("required_user_input_count", 0),
                "리스크": review.get("risk_count", 0),
                "기획서 품질": review.get("prd_quality_score", 0),
                "롤백 대상": ", ".join(review.get("rollback_targets", [])),
                "요약": str(item.get("summary") or review.get("summary") or ""),
            }
        )
    return rows


def reason_preview(reason: str, limit: int = 90) -> str:
    compact = " ".join(str(reason or "").split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit].rstrip()}..."


def rows_for_rollback_events(events: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    rows: list[Dict[str, Any]] = []
    for item in events:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "발생 시각": str(item.get("created_at") or ""),
                "현재 단계": stage_title(str(item.get("from_stage") or "")),
                "되돌린 단계": stage_title(str(item.get("target_stage") or "")),
                "무효화된 단계": ", ".join(
                    stage_title(str(stage_id)) for stage_id in item.get("invalidated_stages", [])
                ),
                "사유 요약": reason_preview(str(item.get("reason") or "")),
            }
        )
    return rows


def approval_button_label(review: Dict[str, Any]) -> str:
    has_warning = (
        review.get("status") == "warning"
        or review.get("required_user_input_count", 0) > 0
        or review.get("risk_count", 0) > 0
        or bool(review.get("rollback_targets"))
    )
    return "경고 확인 후 승인" if has_warning else "검토 후 승인"


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
    message = f"기획서 품질 점수 {score}점 · 자동 보강 {attempted}"
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
        st.info("기획서 패킷이 없는 이전 산출물입니다. 원본 구조화 출력을 확인하세요.")
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
        st.markdown("**개발팀 확인사항**")
        st.dataframe([{"전달사항": item} for item in handoff], width="stretch", hide_index=True)
    else:
        st.info("개발팀 확인사항이 아직 없습니다.")
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
        "## 2. 기획서 핵심 요약",
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
    lines.extend(["", "## 8. 개발팀 확인사항"])
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
            "- 보고 목적: 서비스 기획서 검토 및 개발 회의 안건 정리",
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
            "- 문서명: 서비스 기획서 및 개발 착수 검토안",
            "- 보고 목적: 검토 결과 기반 추진 범위와 개발 회의 안건 확정",
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


REPORT_EXPORTS = {
    "docx": {
        "label": "Word 문서",
        "description": "회의 공유용 편집 문서",
        "file_name": "milemate-final-planning-brief.docx",
        "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "tone": "decision",
    },
    "pdf": {
        "label": "PDF 보고서",
        "description": "인쇄/제출용 고정 문서",
        "file_name": "milemate-final-planning-brief.pdf",
        "mime": "application/pdf",
        "tone": "ready",
    },
    "pptx": {
        "label": "요약 슬라이드",
        "description": "보고·검토용 요약 슬라이드",
        "file_name": "milemate-final-presentation-deck.pptx",
        "mime": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "tone": "technical",
    },
}


def report_export_bytes(session_id: str, export_format: str) -> bytes:
    return api_binary_request("GET", f"/reports/{session_id}/exports/{export_format}")


def html_list(items: Iterable[Any], limit: int = 4) -> str:
    values = [escape(str(item)) for item in list(items)[:limit] if str(item)]
    if not values:
        return "<p>아직 표시할 항목이 없습니다.</p>"
    return "<ul>" + "".join(f"<li>{item}</li>" for item in values) + "</ul>"


def first_text(value: Any, fallback: str = "확인 필요") -> str:
    if isinstance(value, list):
        return str(value[0]) if value else fallback
    if value:
        return str(value)
    return fallback


def report_card_items(report: Dict[str, Any]) -> list[Dict[str, str]]:
    packet = report.get("prd_report", {}) if isinstance(report, dict) else {}
    scope = packet.get("scope", {}) if isinstance(packet.get("scope"), dict) else {}
    risks = report.get("risks", []) if isinstance(report.get("risks"), list) else []
    decisions = (
        report.get("decision_log", [])
        if isinstance(report.get("decision_log"), list)
        else []
    )
    high_risks = [
        item for item in risks if isinstance(item, dict) and item.get("severity") == "high"
    ]
    first_high_risk = high_risks[0].get("description") if high_risks else ""
    return [
        {
            "title": "종합 의견",
            "value": "기획서 초안 준비",
            "detail": str(packet.get("one_page_summary") or "최종 보고서를 생성했습니다.")[:120],
            "tone": "decision",
        },
        {
            "title": "추진 여부",
            "value": "MVP 검토 가능",
            "detail": f"이번 범위 {len(scope.get('in_scope', []))}개 항목을 기준으로 설명합니다.",
            "tone": "ready",
        },
        {
            "title": "핵심 리스크",
            "value": f"{len(risks)}건",
            "detail": (
                first_text(first_high_risk, "회의 전 확인 필요")
                if risks
                else "기록된 리스크가 없습니다."
            ),
            "tone": "risk" if high_risks else "warning",
        },
        {
            "title": "다음 회의 안건",
            "value": f"{len(decisions)}건",
            "detail": first_text(
                decisions[0].get("item") if decisions and isinstance(decisions[0], dict) else "",
                "범위와 데이터 소유자를 확정합니다.",
            ),
            "tone": "technical",
        },
    ]


def render_report_hero(report: Dict[str, Any]) -> None:
    cards = "\n".join(
        f"""
        <div class="report-card report-{escape(card["tone"])}">
          <div class="report-card-title">{escape(card["title"])}</div>
          <div class="report-card-value">{escape(card["value"])}</div>
          <div class="report-card-detail">{escape(card["detail"])}</div>
        </div>
        """
        for card in report_card_items(report)
    )
    st.markdown(
        f"""
        <div class="report-hero">
          <div class="report-kicker">최종 보고서</div>
          <h2>아이디어를 회사 문서 형태로 정리했습니다</h2>
          <p>
            아래 내용은 기획서 본문, 리스크, 개발팀 확인사항, 보고용 산출물로
            바로 나누어 확인할 수 있습니다.
          </p>
          <div class="report-card-grid">{cards}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_prd_overview_boxes(packet: Dict[str, Any]) -> None:
    problem = packet.get("problem", {}) if isinstance(packet.get("problem"), dict) else {}
    scope = packet.get("scope", {}) if isinstance(packet.get("scope"), dict) else {}
    personas = packet.get("personas", []) if isinstance(packet.get("personas"), list) else []
    developer_handoff = packet.get("developer_handoff", [])
    persona_names = [
        item.get("name", item) if isinstance(item, dict) else item
        for item in personas
    ]
    st.markdown(
        f"""
        <div class="report-section-grid">
          <div class="report-section report-decision">
            <div class="report-section-title">문제 정의</div>
            <p>{escape(str(problem.get("customer_pain") or "문제 정의가 필요합니다."))}</p>
          </div>
          <div class="report-section report-ready">
            <div class="report-section-title">대상 사용자</div>
            {html_list(persona_names)}
          </div>
          <div class="report-section report-warning">
            <div class="report-section-title">MVP 범위</div>
            {html_list(scope.get("in_scope", []))}
          </div>
          <div class="report-section report-technical">
            <div class="report-section-title">개발팀 확인사항</div>
            {html_list(developer_handoff)}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_report_export_panel(
    session_id: str,
    report: Dict[str, Any],
    key_prefix: str,
    boxed: bool = True,
    show_json: bool = True,
) -> None:
    st.markdown("### 문서 패키지")
    st.caption("회사에서 실제로 공유하는 형식에 맞춰 편집 문서, 제출 문서, 보고 자료로 나눕니다.")
    cols = st.columns(3)
    for col, export_format in zip(cols, REPORT_EXPORTS):
        config = REPORT_EXPORTS[export_format]
        with col:
            if boxed:
                st.markdown(
                    f"""
                    <div class="export-card export-{escape(config["tone"])}">
                      <div class="export-label">{escape(config["label"])}</div>
                      <div class="export-desc">{escape(config["description"])}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"**{config['label']}**")
                st.caption(config["description"])
            try:
                data = report_export_bytes(session_id, export_format)
                st.download_button(
                    f"{config['label']} 다운로드",
                    data=data,
                    file_name=config["file_name"],
                    mime=config["mime"],
                    key=f"{key_prefix}-{export_format}-{session_id}",
                    width="stretch",
                )
            except RuntimeError as exc:
                st.error(f"{config['label']} 생성 실패: {exc}")

    if show_json:
        with st.expander("원본 데이터", expanded=False):
            st.caption("구조화 결과를 확인하거나 디버깅할 때 사용합니다.")
            st.download_button(
                "JSON 원본 저장",
                data=json.dumps(report, ensure_ascii=False, indent=2),
                file_name="milemate-final-report.json",
                mime="application/json",
                key=f"{key_prefix}-json-{session_id}",
                width="stretch",
            )


def rollback_recommendation_text(output: Dict[str, Any], review: Dict[str, Any]) -> str:
    planner_view = output.get("planner_view", {})
    recommendation = ""
    if isinstance(planner_view, dict):
        recommendation = str(planner_view.get("rollback_recommendation") or "")
    if recommendation and recommendation != "None":
        return stage_title(recommendation) if recommendation in STAGE_IDS else recommendation
    targets = review.get("rollback_targets") or []
    if targets:
        return ", ".join(
            stage_title(stage_id) if stage_id in STAGE_IDS else stage_id
            for stage_id in targets
        )
    return "롤백 권고 없음"


def render_review_summary(
    stage_id: str,
    output: Dict[str, Any],
    review: Dict[str, Any],
    bordered: bool = True,
) -> None:
    required = as_string_list(output.get("required_user_input"))
    risks = output.get("risks", []) if isinstance(output.get("risks"), list) else []
    decisions = (
        output.get("decision_points", [])
        if isinstance(output.get("decision_points"), list)
        else []
    )
    rollback_text = rollback_recommendation_text(output, review)

    def render_content() -> None:
        st.markdown(f"### 검토/결정 요약 · {stage_title(stage_id)}")
        if review.get("summary"):
            st.write(review["summary"])

        metric_cols = st.columns(4)
        metric_cols[0].metric("추가 입력", review.get("required_user_input_count", 0))
        metric_cols[1].metric("리스크", review.get("risk_count", 0))
        metric_cols[2].metric("기획서 품질", review.get("prd_quality_score", 0))
        metric_cols[3].metric("롤백 권고", rollback_text)

        if required:
            st.warning("추가 입력 확인 필요")
            st.dataframe(
                [{"확인할 내용": item} for item in required],
                width="stretch",
                hide_index=True,
            )
        if risks:
            st.warning("리스크 확인 필요")
            st.dataframe(rows_for_risks(risks), width="stretch", hide_index=True)
        if decisions:
            st.markdown("**승인 전 결정 항목**")
            st.dataframe(rows_for_decisions(decisions), width="stretch", hide_index=True)

    if bordered:
        with st.container(border=True):
            render_content()
    else:
        render_content()


def approve_current_stage(session: Dict[str, Any]) -> None:
    previous_stage = session["current_stage"]
    st.session_state["session"] = api_request(
        "POST",
        "/stages/approve",
        {"session_id": session["session_id"]},
    )
    st.session_state["stage_response"] = None
    st.session_state["selected_stage_id"] = st.session_state["session"]["current_stage"]
    if previous_stage == "stage_4":
        st.session_state["report"] = api_request(
            "GET",
            f"/reports/{session['session_id']}",
        )


def rollback_current_stage(session: Dict[str, Any], target_stage: str, reason: str) -> None:
    st.session_state["session"] = api_request(
        "POST",
        "/stages/rollback",
        {
            "session_id": session["session_id"],
            "target_stage": target_stage,
            "reason": reason,
        },
    )
    st.session_state["stage_response"] = None
    st.session_state["report"] = None
    st.session_state["selected_stage_id"] = st.session_state["session"]["current_stage"]


@st.dialog("이전 단계로 되돌리기")
def render_rollback_dialog(
    session: Dict[str, Any],
    rollback_targets: list[str],
    is_generating: bool,
) -> None:
    stage_id = session["current_stage"]
    key_prefix = f"rollback:{session['session_id']}:{stage_id}"
    st.write(
        "현재 단계에서 발견한 문제를 바탕으로 이전 단계의 기획 가정을 다시 수정합니다. "
        "사유에는 단순 키워드보다 잘못된 가정, 수정 지시, 유지할 결정을 함께 적어주세요."
    )
    target = st.selectbox(
        "되돌릴 단계",
        rollback_targets,
        key=f"{key_prefix}:target",
        format_func=stage_title,
        disabled=is_generating,
    )
    reason = st.text_area(
        "롤백 사유 및 수정 지시",
        height=240,
        key=f"{key_prefix}:reason",
        placeholder=ROLLBACK_REASON_PLACEHOLDER,
        disabled=is_generating,
    )
    st.caption(
        "이 내용은 진행 로그와 최종 의사결정 이력에 남습니다. "
        "다음 생성 단계에서 Codex가 반영해야 할 지시까지 자세히 남기는 것이 좋습니다."
    )
    submit_col, cancel_col = st.columns([1.2, 1])
    with submit_col:
        if st.button(
            "이 사유로 되돌리기",
            type="primary",
            width="stretch",
            disabled=is_generating or not reason.strip(),
        ):
            try:
                clear_error()
                st.session_state.pop("rollback_dialog_context", None)
                rollback_current_stage(session, target, reason.strip())
                st.rerun()
            except RuntimeError as exc:
                set_error(str(exc))
    with cancel_col:
        if st.button("취소", width="stretch", disabled=is_generating):
            st.session_state.pop("rollback_dialog_context", None)
            st.rerun()


def render_current_decision_panel(
    session: Dict[str, Any],
    current_response: Dict[str, Any] | None,
    is_generating: bool,
) -> None:
    stage_id = session["current_stage"]
    output = current_response.get("output", {}) if current_response else {}
    review = stage_review_state(session, stage_id, output)
    if not current_response:
        review = {
            **review,
            "status": "pending",
            "required_user_input_count": 0,
            "risk_count": 0,
            "rollback_targets": [],
        }

    with st.container(border=True):
        st.markdown(f"### 기획서 검토 · {stage_title(stage_id)}")
        if not current_response:
            st.caption("아직 생성된 결과가 없습니다. 위 생성 영역에서 현재 단계를 먼저 만듭니다.")
        else:
            render_review_summary(stage_id, output, review, bordered=False)

        action_cols = st.columns([1.4, 1, 2.8])
        with action_cols[0]:
            can_approve = stage_id in session.get("stage_outputs", {})
            if st.button(
                approval_button_label(review),
                type="primary",
                width="stretch",
                disabled=not can_approve or is_generating,
            ):
                try:
                    clear_error()
                    approve_current_stage(session)
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

        rollback_targets = review.get("rollback_targets", [])
        if rollback_targets:
            with action_cols[2]:
                target_labels = ", ".join(stage_title(target) for target in rollback_targets)
                st.caption(f"되돌릴 수 있는 단계: {target_labels}")
                if st.button(
                    "이전 단계로 되돌리기",
                    width="stretch",
                    disabled=is_generating,
                    key=f"rollback-open-{session['session_id']}-{stage_id}",
                ):
                    st.session_state["rollback_dialog_context"] = {
                        "session_id": session["session_id"],
                        "stage_id": stage_id,
                    }
        dialog_context = st.session_state.get("rollback_dialog_context")
        if (
            rollback_targets
            and isinstance(dialog_context, dict)
            and dialog_context.get("session_id") == session["session_id"]
            and dialog_context.get("stage_id") == stage_id
        ):
            render_rollback_dialog(session, rollback_targets, is_generating)


def render_stage_output(
    stage_response: Dict[str, Any],
    session: Dict[str, Any] | None = None,
) -> None:
    output = stage_response.get("output", {})
    stage_id = stage_response.get("stage_id", "")
    packet = output.get("prd_packet", {})
    quality = output.get("prd_quality", {})
    review = stage_review_state(session or {"stage_outputs": {stage_id: output}}, stage_id, output)
    if not session or stage_id != session.get("current_stage"):
        render_review_summary(stage_id, output, review)
    st.subheader(f"{stage_title(stage_id)} 상세 산출물")

    tab_labels = [
        "결정/리스크",
        "기획서 초안",
        "구현 검토",
        "내보내기",
    ]
    decisions_tab, prd_tab, handoff_tab, raw_tab = st.tabs(tab_labels)
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
    with prd_tab:
        render_prd_packet(packet, quality)
        if has_prd_packet(packet):
            render_prd_execution(packet)
        else:
            render_key_values(output.get("planner_view", {}))
    with handoff_tab:
        if has_prd_packet(packet):
            render_prd_data(packet)
            render_prd_handoff(packet)
        else:
            render_key_values(output.get("engineer_view", {}))
    with raw_tab:
        citations = output.get("citations", [])
        if citations:
            st.markdown("**근거 자료**")
            st.dataframe(rows_for_citations(citations), width="stretch", hide_index=True)
        else:
            st.info("이 산출물에 연결된 근거 자료가 없습니다.")
        render_downloads(stage_id, output, key_prefix="stage-detail")
        st.markdown("**기획 브리프 원본**")
        render_key_values(output.get("planner_view", {}))
        st.markdown("**실행 전환본 원본**")
        render_key_values(output.get("engineer_view", {}))


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
                st.dataframe(rows_for_stage_history(session), width="stretch", hide_index=True)
            if rollback_events:
                st.markdown("**되돌림 기록**")
                st.dataframe(
                    rows_for_rollback_events(rollback_events),
                    width="stretch",
                    hide_index=True,
                )
                for idx, event in enumerate(rollback_events, start=1):
                    target_stage = stage_title(str(event.get("target_stage") or ""))
                    with st.expander(f"되돌림 상세 사유 {idx} · {target_stage}", expanded=False):
                        st.markdown("**롤백 사유 및 수정 지시**")
                        st.write(str(event.get("reason") or "사유가 기록되지 않았습니다."))


def render_stage_navigator(session: Dict[str, Any]) -> str:
    selected = ensure_selected_stage(session)
    st.subheader("스테이지 탐색")
    selected = st.radio(
        "열람할 스테이지",
        STAGE_IDS,
        index=STAGE_IDS.index(selected),
        format_func=lambda stage_id: stage_nav_label(session, stage_id),
        horizontal=True,
    )
    st.session_state["selected_stage_id"] = selected

    cols = st.columns(len(STAGE_IDS))
    for idx, stage_id in enumerate(STAGE_IDS):
        with cols[idx]:
            with st.container(border=True):
                st.markdown(f"**{stage_title(stage_id)}**")
                st.caption(stage_status(session, stage_id))
    return selected


def render_stage_placeholder(session: Dict[str, Any], stage_id: str) -> None:
    with st.container(border=True):
        st.subheader(f"{stage_title(stage_id)} 산출물")
        if stage_id == session["current_stage"]:
            st.info(
                "이 단계의 산출물이 아직 없습니다. "
                "상단의 Codex 생성 영역에서 바로 생성할 수 있습니다."
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
            st.caption("승인된 스테이지 결과를 묶은 문서 패키지입니다.")
            render_report_export_panel(
                session_id=session["session_id"],
                report=report,
                key_prefix="artifact-report",
                boxed=False,
                show_json=False,
            )


def render_report(report: Dict[str, Any], session_id: str | None = None) -> None:
    render_report_hero(report)
    if session_id:
        render_report_export_panel(
            session_id=session_id,
            report=report,
            key_prefix="main-report",
            boxed=True,
            show_json=True,
        )
    prd_tab, risk_tab, engineer_tab, log_tab = st.tabs(
        ["기획서 본문", "리스크/결정", "개발팀 전달", "원본 구조"]
    )
    with prd_tab:
        packet = report.get("prd_report", {})
        if has_prd_packet(packet):
            render_prd_overview_boxes(packet)
            render_prd_packet(packet, report.get("prd_quality", {}))
            render_prd_execution(packet)
        else:
            render_key_values(report.get("planner_report", {}))
    with risk_tab:
        risks = report.get("risks", [])
        if risks:
            st.markdown("**핵심 리스크**")
            st.dataframe(rows_for_risks(risks), width="stretch", hide_index=True)
        else:
            st.success("등록된 리스크가 없습니다.")
        st.markdown("**의사결정 이력**")
        st.dataframe(
            rows_for_decisions(report.get("decision_log", [])),
            width="stretch",
            hide_index=True,
        )
    with engineer_tab:
        packet = report.get("prd_report", {})
        if has_prd_packet(packet):
            render_prd_data(packet)
            render_prd_handoff(packet)
        render_key_values(report.get("engineer_report", {}))
    with log_tab:
        render_key_values(report.get("planner_report", {}))
        citations = report.get("citations", [])
        if citations:
            st.markdown("**참고자료**")
            st.dataframe(rows_for_citations(citations), width="stretch", hide_index=True)


def set_error(message: str) -> None:
    st.session_state["error"] = message


def clear_error() -> None:
    st.session_state["error"] = ""


def sync_input_to_scenario() -> None:
    scenario_id = st.session_state["scenario_id"]
    st.session_state["user_input"] = scenario_initial_input(
        st.session_state["demo_inputs"],
        scenario_id,
    )
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

    messages = stage_chat_messages(session_id, stage_id)
    with st.container(border=True):
        st.markdown(f"### 기획서 초안 작성 · {stage_title(stage_id)}")
        st.caption(
            "이 단계 산출물이 아직 없거나 다시 생성하려는 경우 "
                "아래 요청으로 바로 작성합니다."
        )
        if context:
            st.info(f"검증 조건: {display_value(context)}")

        input_col, send_col = st.columns([5, 1.25], gap="small", vertical_alignment="bottom")
        with input_col:
            st.text_area(
                "기획자 추가 요청",
                height=122,
                key=draft_key,
                placeholder=f"{stage_title(stage_id)} 기획서에 반영할 내용을 입력하세요",
                disabled=st.session_state.get("is_generating", False),
            )
        with send_col:
            if st.button(
                "Codex로 기획서 생성",
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

        if messages:
            with st.expander("이 단계 대화 로그", expanded=False):
                for message in messages:
                    role = "assistant" if message["role"] == "assistant" else "user"
                    with st.chat_message(role):
                        st.markdown(message["content"])


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


def generation_runtime_copy() -> str:
    status = fetch_runtime_status()
    if status.get("mode") == "local":
        return "로컬 리허설 모드에서 기획서 작성 흐름을 재현합니다."
    if status.get("available"):
        return "라이브 Codex가 아이디어를 단계별 기획서 초안으로 구조화합니다."
    return "라이브 연결 상태를 확인하지 못했습니다. 생성 실패 시 실행 상태를 확인하세요."


def start_stage_generation(
    session: Dict[str, Any],
    base_input: str,
    context: Dict[str, Any],
) -> None:
    started_at = time.time()
    st.session_state["pending_stage_run"] = {
        "session_id": session["session_id"],
        "stage_id": session["current_stage"],
        "user_input": build_stage_user_input(session, base_input),
        "context": context,
        "started_at": started_at,
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
        <div class="generation-panel">
            {generation_visual_markup()}
          <div>
            <strong>Codex가 기획서 초안을 작성 중입니다</strong>
            <div class="generation-copy">
              {escape(generation_runtime_copy())}
            </div>
            <div class="generation-dots"><span></span><span></span><span></span></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.status(f"{stage_title(stage_id)} 생성 중", expanded=True) as status:
        st.write("아이디어 맥락 정리")
        st.write("유사 사례와 리스크 확인")
        st.write("기획서 형식 점검")
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
        .block-container { max-width: 1180px; padding-top: 1.25rem; }
        .product-intro {
          border-top: 1px solid #d8dee4;
          border-bottom: 1px solid #d8dee4;
          padding: 14px 0 16px;
          margin: 0 0 16px;
        }
        .product-kicker {
          color: #0969da;
          font-size: 0.78rem;
          font-weight: 800;
          letter-spacing: 0;
          margin-bottom: 4px;
        }
        .product-copy {
          color: #24292f;
          font-size: 1.02rem;
          line-height: 1.55;
          max-width: 860px;
        }
        .runtime-badge {
          border: 1px solid #d0d7de;
          padding: 12px 14px;
      margin: 4px 0 18px;
      background: #f6f8fa;
    }
    .runtime-local {
      border-left: 5px solid #57606a;
      background: #f6f8fa;
    }
    .runtime-live {
      border-left: 5px solid #1a7f37;
      background: #eefbea;
    }
    .runtime-warning {
      border-left: 5px solid #bf8700;
      background: #fff8c5;
    }
    .runtime-kicker {
      color: #57606a;
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0;
    }
    .runtime-label {
      color: #24292f;
      font-size: 1rem;
      font-weight: 700;
      margin-top: 2px;
    }
    .runtime-detail,
    .runtime-endpoint {
      color: #57606a;
      font-size: 0.86rem;
      margin-top: 2px;
    }
    .demo-brief {
      border: 1px solid #d8dee4;
      background: #ffffff;
      padding: 22px 24px;
      margin: 8px 0 18px;
    }
    .demo-brief h2 {
      color: #24292f;
      font-size: 1.55rem;
      line-height: 1.25;
      margin: 3px 0 8px;
      letter-spacing: 0;
    }
    .demo-kicker {
      color: #0969da;
      font-size: 0.76rem;
      font-weight: 800;
      letter-spacing: 0;
    }
    .demo-subtitle {
      color: #57606a;
      font-weight: 650;
    }
    .report-hero {
      border: 1px solid #d8dee4;
      background: #ffffff;
      padding: 20px 22px;
      margin: 8px 0 18px;
      border-radius: 8px;
    }
    .report-kicker {
      color: #0969da;
      font-size: 0.76rem;
      font-weight: 800;
      letter-spacing: 0;
      margin-bottom: 3px;
    }
    .report-hero h2 {
      color: #24292f;
      font-size: 1.45rem;
      line-height: 1.3;
      margin: 0 0 6px;
      letter-spacing: 0;
    }
    .report-hero p {
      color: #57606a;
      margin: 0 0 14px;
      line-height: 1.55;
    }
    .report-card-grid,
    .report-section-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }
    .report-card,
    .report-section,
    .export-card {
      border: 1px solid #d8dee4;
      border-left-width: 5px;
      background: #ffffff;
      padding: 12px 13px;
      border-radius: 8px;
      min-height: 112px;
    }
    .report-card-title,
    .report-section-title,
    .export-label {
      color: #24292f;
      font-size: 0.84rem;
      font-weight: 800;
      letter-spacing: 0;
      margin-bottom: 5px;
    }
    .report-card-value {
      color: #24292f;
      font-size: 1.05rem;
      font-weight: 800;
      margin-bottom: 5px;
    }
    .report-card-detail,
    .export-desc,
    .report-section p,
    .report-section li {
      color: #57606a;
      font-size: 0.88rem;
      line-height: 1.45;
    }
    .report-section ul {
      margin: 0;
      padding-left: 1.05rem;
    }
    .report-decision,
    .export-decision { border-left-color: #0969da; background: #f6fbff; }
    .report-ready,
    .export-ready { border-left-color: #1a7f37; background: #f3fbf1; }
    .report-warning,
    .export-warning { border-left-color: #bf8700; background: #fffbea; }
    .report-risk,
    .export-risk { border-left-color: #cf222e; background: #fff5f5; }
    .report-technical,
    .export-technical { border-left-color: #57606a; background: #f6f8fa; }
    .export-card {
      min-height: 82px;
      margin-bottom: 8px;
    }
    div[data-testid="stMetric"] {
      border: 1px solid #d8dee4;
      background: #f6f8fa;
      padding: 10px 12px;
    }
    div[data-testid="stMetric"] label { color: #57606a; }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .generation-panel {
      display: flex;
      align-items: center;
      gap: 20px;
      border: 1px solid #b6d4fe;
      background: #eef6ff;
      padding: 18px 20px;
      margin: 12px 0 16px;
    }
    .generation-panel strong {
      display: block;
      font-size: 1rem;
      color: #1f2d3d;
    }
    .generation-copy {
      color: #425466;
      font-size: 0.92rem;
      margin-top: 2px;
    }
    .generation-orbit {
      width: 32px;
      height: 32px;
      border: 3px solid #b6d4fe;
      border-top-color: #0969da;
      border-radius: 50%;
      animation: spin 0.9s linear infinite;
      flex: 0 0 auto;
    }
    .generation-cat-sprite {
      width: clamp(136px, 18vw, 184px);
      height: clamp(136px, 18vw, 184px);
      flex: 0 0 clamp(136px, 18vw, 184px);
      background-repeat: no-repeat;
      background-size: 400% 200%;
      background-position: 0% 0%;
      border-radius: 16px;
      box-shadow:
        inset 0 0 0 1px rgba(9, 105, 218, 0.12),
        0 8px 18px rgba(31, 35, 40, 0.1);
      animation: catYarnFrames 1.35s steps(1) infinite;
    }
    .generation-dots span {
      display: inline-block;
      width: 6px;
      height: 6px;
      margin-right: 4px;
      background: #0969da;
      border-radius: 50%;
      animation: pulse 1.2s ease-in-out infinite;
    }
    .generation-dots span:nth-child(2) { animation-delay: 0.18s; }
    .generation-dots span:nth-child(3) { animation-delay: 0.36s; }
    @keyframes spin { to { transform: rotate(360deg); } }
    @keyframes catYarnFrames {
      0%, 12.49% { background-position: 0% 0%; }
      12.5%, 24.99% { background-position: 33.333% 0%; }
      25%, 37.49% { background-position: 66.666% 0%; }
      37.5%, 49.99% { background-position: 100% 0%; }
      50%, 62.49% { background-position: 0% 100%; }
      62.5%, 74.99% { background-position: 33.333% 100%; }
      75%, 87.49% { background-position: 66.666% 100%; }
      87.5%, 100% { background-position: 100% 100%; }
    }
    @keyframes pulse {
      0%, 80%, 100% { opacity: 0.25; transform: translateY(0); }
      40% { opacity: 1; transform: translateY(-3px); }
    }
    @media (max-width: 900px) {
      .report-card-grid,
      .report-section-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }
    @media (max-width: 640px) {
      .report-card-grid,
      .report-section-grid {
        grid-template-columns: 1fr;
      }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Milemate")
render_product_intro()

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
    st.session_state["user_input"] = scenario_initial_input(demo_inputs, default_scenario)
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
        "적용 예시",
        options=list(scenarios),
        format_func=lambda key: (
            scenario_display_title(demo_inputs, key)
            if key in demo_inputs
            else scenarios[key]["label"]
        ),
        key="scenario_id",
        on_change=sync_input_to_scenario,
    )
    user_input = st.text_area(
        "기획자의 아이디어 메모",
        height=92,
        key="user_input",
    )
    render_demo_brief_block(scenario_brief(demo_inputs, scenario_id), compact=True)
    st.divider()
    verification_preset = st.selectbox(
        "검증에서 드러낼 리스크",
        options=list(VERIFICATION_PRESETS),
        format_func=lambda key: VERIFICATION_PRESET_LABELS.get(key, key),
        key="verification_preset",
    )
    if st.button("기획서 작성 시작", type="primary", width="stretch"):
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
    with st.expander("실행 상태", expanded=False):
        render_runtime_badge(fetch_runtime_status())
    st.caption("로컬 리허설 모드" if API_MODE == "local" else f"백엔드 {API_BASE_URL}")

if st.session_state["error"]:
    st.error(st.session_state["error"])

session = st.session_state["session"]
if not session:
    render_demo_brief_block(scenario_brief(demo_inputs, scenario_id))
    st.info("왼쪽 사이드바에서 적용 예시와 아이디어 메모를 확인한 뒤 기획서 작성을 시작하세요.")
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

is_generating = st.session_state.get("is_generating", False)
generation_context = build_generation_context(
    session=session,
    verification_preset=verification_preset,
    demo_inputs=demo_inputs,
    scenario_id=scenario_id,
)
render_stage_chat(session, scenario_id, user_input, generation_context)
current_response = current_stage_response(session)
render_current_decision_panel(session, current_response, is_generating)

selected_stage_id = render_stage_navigator(session)

selected_stage_response = stage_response_for(session, selected_stage_id)
workspace_cols = st.columns([2.2, 1], gap="large")
with workspace_cols[0]:
    if selected_stage_response:
        render_stage_output(selected_stage_response, session)
    else:
        render_stage_placeholder(session, selected_stage_id)

    if st.session_state["report"]:
        render_report(st.session_state["report"], session_id=session["session_id"])

with workspace_cols[1]:
    render_artifact_library(session, st.session_state["report"])
