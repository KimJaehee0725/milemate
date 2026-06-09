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


def test_streamlit_start_run_approve_smoke(monkeypatch):
    app = run_app(monkeypatch)

    assert app.info[0].value == "왼쪽 사이드바에서 세션을 시작하세요."
    button_by_label(app, "세션 시작").click().run(timeout=5)

    assert metrics(app)["현재 단계"] == "1단계 문제 정의"
    assert button_by_label(app, "승인 / 다음").disabled is True
    assert "강남/서초 피크타임" in text_area_by_label(app, "대화 입력").value
    assert all(button.label != "단계 생성" for button in app.button)

    button_by_label(app, "전송 및 생성").click().run(timeout=10)
    assert any("강남/서초 피크타임" in item.value for item in app.markdown)

    assert metrics(app)["생성 결과"] == "1"
    assert button_by_label(app, "승인 / 다음").disabled is False
    assert any("생성 완료:" in item.value for item in app.markdown)

    button_by_label(app, "승인 / 다음").click().run(timeout=5)

    assert metrics(app)["현재 단계"] == "2단계 서비스 구조"
    assert metrics(app)["승인됨"] == "1"
    assert button_by_label(app, "승인 / 다음").disabled is True
    assert "완전 자동 배차" in text_area_by_label(app, "대화 입력").value


def test_streamlit_stage_3_preset_rollback_clears_stale_output(monkeypatch):
    app = run_app(monkeypatch)
    button_by_label(app, "세션 시작").click().run(timeout=5)

    for _ in range(2):
        button_by_label(app, "전송 및 생성").click().run(timeout=10)
        button_by_label(app, "승인 / 다음").click().run(timeout=5)

    assert metrics(app)["현재 단계"] == "3단계 검증"
    app.selectbox[1].set_value("Missing data").run(timeout=5)
    button_by_label(app, "전송 및 생성").click().run(timeout=10)

    assert metrics(app)["생성 결과"] == "3"
    assert any(button.label == "롤백" for button in app.button)

    app.selectbox[0].set_value("stage_2").run(timeout=5)
    button_by_label(app, "롤백").click().run(timeout=5)

    assert metrics(app)["현재 단계"] == "2단계 서비스 구조"
    assert metrics(app)["생성 결과"] == "1"
    assert button_by_label(app, "승인 / 다음").disabled is True


def test_streamlit_can_view_previous_stage_output(monkeypatch):
    app = run_app(monkeypatch)
    button_by_label(app, "세션 시작").click().run(timeout=5)

    button_by_label(app, "전송 및 생성").click().run(timeout=10)
    button_by_label(app, "승인 / 다음").click().run(timeout=5)

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
        app.selectbox[0].set_value(scenario_id).run(timeout=5)
        button_by_label(app, "세션 시작").click().run(timeout=5)

        assert expected_copy in text_area_by_label(app, "대화 입력").value
