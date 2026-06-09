from streamlit.testing.v1 import AppTest

APP_PATH = "app/frontend/streamlit_app.py"


def run_app(monkeypatch):
    monkeypatch.setenv("MILEMATE_API_MODE", "local")
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=5)
    return app


def metrics(app):
    return {item.label: item.value for item in app.metric}


def button_by_label(app, label):
    for button in app.button:
        if button.label == label:
            return button
    raise AssertionError(f"button not found: {label}")


def text_area_by_label(app, label):
    for text_area in app.text_area:
        if text_area.label == label:
            return text_area
    raise AssertionError(f"text area not found: {label}")


def selectbox_by_label(app, label):
    for selectbox in app.selectbox:
        if selectbox.label == label:
            return selectbox
    raise AssertionError(f"selectbox not found: {label}")


def enabled_button_by_label(app, labels):
    for button in app.button:
        if button.label in labels and not button.disabled:
            return button
    raise AssertionError(f"enabled button not found: {labels}")


def test_streamlit_start_run_approve_smoke(monkeypatch):
    app = run_app(monkeypatch)

    assert (
        app.info[0].value
        == "왼쪽 사이드바에서 적용 예시와 아이디어 메모를 확인한 뒤 기획서 작성을 시작하세요."
    )
    assert any("비개발 기획자를 위한 기술기획서 작성 보조" in item.value for item in app.markdown)
    assert any("CleanGo 적용 예시: 피크타임 배차 추천" in item.value for item in app.markdown)
    button_by_label(app, "기획서 작성 시작").click().run(timeout=5)

    assert metrics(app)["현재 단계"] == "1단계 문제 정의"
    assert button_by_label(app, "검토 후 승인").disabled is True
    assert "강남/서초 피크타임" in text_area_by_label(app, "기획자 추가 요청").value
    assert all(button.label != "단계 생성" for button in app.button)

    button_by_label(app, "Codex로 기획서 생성").click().run(timeout=10)
    assert any("강남/서초 피크타임" in item.value for item in app.markdown)

    assert metrics(app)["생성 결과"] == "1"
    assert button_by_label(app, "경고 확인 후 승인").disabled is False
    assert any("생성 완료:" in item.value for item in app.markdown)
    assert any("추가 입력 확인 필요" in item.value for item in app.warning)

    button_by_label(app, "경고 확인 후 승인").click().run(timeout=5)

    assert metrics(app)["현재 단계"] == "2단계 서비스 구조"
    assert metrics(app)["승인됨"] == "1"
    assert button_by_label(app, "검토 후 승인").disabled is True
    assert "완전 자동 배차" in text_area_by_label(app, "기획자 추가 요청").value


def test_streamlit_stage_3_preset_rollback_clears_stale_output(monkeypatch):
    app = run_app(monkeypatch)
    button_by_label(app, "기획서 작성 시작").click().run(timeout=5)

    for _ in range(2):
        button_by_label(app, "Codex로 기획서 생성").click().run(timeout=10)
        button_by_label(app, "경고 확인 후 승인").click().run(timeout=5)

    assert metrics(app)["현재 단계"] == "3단계 검증"
    selectbox_by_label(app, "검증에서 드러낼 리스크").set_value("Missing data").run(timeout=5)
    button_by_label(app, "Codex로 기획서 생성").click().run(timeout=10)

    assert metrics(app)["생성 결과"] == "3"
    assert button_by_label(app, "경고 확인 후 승인").disabled is False
    assert any(button.label == "이전 단계로 되돌리기" for button in app.button)

    button_by_label(app, "이전 단계로 되돌리기").click().run(timeout=5)
    selectbox_by_label(app, "되돌릴 단계").set_value("stage_2").run(timeout=5)
    rollback_reason = (
        "발견한 문제: 데이터 출처가 비어 있어 3단계 검증을 통과시키기 어렵습니다.\n\n"
        "잘못된 가정: 2단계 MVP 범위가 충분한 주문/운영 데이터를 이미 확보했다고 봤습니다.\n\n"
        "되돌아가 수정할 내용: 2단계에서 필요한 데이터 소유자와 수집 주기를 먼저 확정하고, "
        "데이터가 없는 기능은 MVP 밖으로 빼주세요.\n\n"
        "다음 단계에서 유지할 내용: 운영자 승인형 추천이라는 큰 방향은 유지합니다."
    )
    text_area_by_label(app, "롤백 사유 및 수정 지시").set_value(rollback_reason).run(timeout=5)
    button_by_label(app, "이 사유로 되돌리기").click().run(timeout=5)

    assert metrics(app)["현재 단계"] == "2단계 서비스 구조"
    assert metrics(app)["생성 결과"] == "1"
    assert button_by_label(app, "검토 후 승인").disabled is True
    assert any("되돌림 상세 사유" in item.label for item in app.expander)


def test_streamlit_can_view_previous_stage_output(monkeypatch):
    app = run_app(monkeypatch)
    button_by_label(app, "기획서 작성 시작").click().run(timeout=5)

    button_by_label(app, "Codex로 기획서 생성").click().run(timeout=10)
    button_by_label(app, "경고 확인 후 승인").click().run(timeout=5)

    assert metrics(app)["현재 단계"] == "2단계 서비스 구조"
    assert app.radio[0].value == "stage_2"

    app.radio[0].set_value("stage_1").run(timeout=5)

    assert metrics(app)["현재 단계"] == "2단계 서비스 구조"
    assert app.radio[0].value == "stage_1"
    assert any("문제와 KPI 프레임을 정리" in item.value for item in app.markdown)


def test_streamlit_prefills_demo_chat_by_scenario(monkeypatch):
    app = run_app(monkeypatch)

    expectations = {
        "dispatch_recommendation": "강남/서초 피크타임",
        "eta_prediction": "도착 시간을 신뢰",
        "failed_delivery_risk": "배송 실패는",
    }
    for scenario_id, expected_copy in expectations.items():
        selectbox_by_label(app, "적용 예시").set_value(scenario_id).run(timeout=5)
        button_by_label(app, "기획서 작성 시작").click().run(timeout=5)

        assert expected_copy in text_area_by_label(app, "기획자 추가 요청").value


def test_streamlit_final_report_shows_business_exports(monkeypatch):
    app = run_app(monkeypatch)
    button_by_label(app, "기획서 작성 시작").click().run(timeout=5)

    for _ in range(4):
        button_by_label(app, "Codex로 기획서 생성").click().run(timeout=10)
        enabled_button_by_label(app, {"경고 확인 후 승인", "검토 후 승인"}).click().run(timeout=8)

    assert any("아이디어를 회사 문서 형태로 정리했습니다" in item.value for item in app.markdown)
    assert any("문서 패키지" in item.value for item in app.markdown)
    assert any("Word 문서" in item.value for item in app.markdown)
    assert any("PDF 보고서" in item.value for item in app.markdown)
    assert any("요약 슬라이드" in item.value for item in app.markdown)
    assert any("원본 데이터" in item.label for item in app.expander)
