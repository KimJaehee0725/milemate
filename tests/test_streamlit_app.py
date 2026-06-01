from streamlit.testing.v1 import AppTest

APP_PATH = "app/frontend/streamlit_app.py"


def run_app(monkeypatch):
    monkeypatch.setenv("MILEMATE_API_MODE", "local")
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=5)
    return app


def metrics(app):
    return {item.label: item.value for item in app.metric}


def test_streamlit_start_run_approve_smoke(monkeypatch):
    app = run_app(monkeypatch)

    assert app.info[0].value == "Start a session from the sidebar."
    app.button[0].click().run(timeout=5)

    assert metrics(app)["Current stage"] == "stage_1"
    assert app.button[1].label == "Approve / Next"
    assert app.button[1].disabled is True

    app.button[0].click().run(timeout=5)

    assert metrics(app)["Outputs"] == "1"
    assert app.button[1].disabled is False

    app.button[1].click().run(timeout=5)

    assert metrics(app)["Current stage"] == "stage_2"
    assert metrics(app)["Approved"] == "1"
    assert app.button[1].disabled is True


def test_streamlit_stage_3_preset_rollback_clears_stale_output(monkeypatch):
    app = run_app(monkeypatch)
    app.button[0].click().run(timeout=5)

    for _ in range(2):
        app.button[0].click().run(timeout=5)
        app.button[1].click().run(timeout=5)

    assert metrics(app)["Current stage"] == "stage_3"
    app.selectbox[1].set_value("Missing data").run(timeout=5)
    app.button[0].click().run(timeout=5)

    assert metrics(app)["Outputs"] == "3"
    assert any(button.label == "Rollback" for button in app.button)

    app.selectbox[0].set_value("stage_2").run(timeout=5)
    app.button[3].click().run(timeout=5)

    assert metrics(app)["Current stage"] == "stage_2"
    assert metrics(app)["Outputs"] == "1"
    assert app.button[1].disabled is True
