from fastapi.testclient import TestClient

from app.backend.main import create_app


def make_client():
    return TestClient(create_app())


def test_session_routes_reject_unknown_session_ids():
    client = make_client()
    missing_session_id = "missing-session-for-test"

    session_response = client.get(f"/sessions/{missing_session_id}")
    assert session_response.status_code == 404
    assert session_response.json()["detail"]["code"] == "unknown_session"

    run_response = client.post("/stages/run", json={"session_id": missing_session_id})
    assert run_response.status_code == 404

    approve_response = client.post("/stages/approve", json={"session_id": missing_session_id})
    assert approve_response.status_code == 404

    report_response = client.get(f"/reports/{missing_session_id}")
    assert report_response.status_code == 404


def test_create_session_rejects_unknown_scenario():
    client = make_client()

    response = client.post("/sessions", json={"scenario": "unknown_scenario"})

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "unknown_scenario"
    assert "unknown scenario" in response.json()["detail"]["message"]


def test_dispatch_happy_path_runs_stage_1_to_report():
    client = make_client()

    create_response = client.post(
        "/sessions",
        json={
            "scenario": "dispatch_recommendation",
            "user_input": "peak-time dispatch bottleneck",
        },
    )
    assert create_response.status_code == 201
    session = create_response.json()
    session_id = session["session_id"]
    assert session["current_stage"] == "stage_1"

    expected_stages = ["stage_1", "stage_2", "stage_3", "stage_4"]
    for stage_id in expected_stages:
        run_response = client.post("/stages/run", json={"session_id": session_id})
        assert run_response.status_code == 200
        stage_response = run_response.json()
        assert stage_response["stage_id"] == stage_id
        assert stage_response["output"]["summary"]
        assert "planner_view" in stage_response["output"]
        assert "engineer_view" in stage_response["output"]

        approve_response = client.post("/stages/approve", json={"session_id": session_id})
        assert approve_response.status_code == 200

    report_response = client.get(f"/reports/{session_id}")
    assert report_response.status_code == 200
    report = report_response.json()
    assert report["planner_report"]["problem_redefinition"]
    assert report["engineer_report"]["required_data"]
    assert report["decision_log"]


def test_dispatch_api_allows_configured_stage_3_to_stage_2_rollback():
    client = make_client()
    session = client.post(
        "/sessions",
        json={"scenario": "dispatch_recommendation"},
    ).json()
    session_id = session["session_id"]

    for expected_stage in ["stage_1", "stage_2"]:
        run_response = client.post("/stages/run", json={"session_id": session_id})
        assert run_response.status_code == 200
        assert run_response.json()["stage_id"] == expected_stage

        approve_response = client.post("/stages/approve", json={"session_id": session_id})
        assert approve_response.status_code == 200

    stage_3_response = client.post("/stages/run", json={"session_id": session_id})
    assert stage_3_response.status_code == 200
    assert stage_3_response.json()["stage_id"] == "stage_3"
    assert "stage_2" in stage_3_response.json()["output"]["rollback_targets"]

    rollback_response = client.post(
        "/stages/rollback",
        json={
            "session_id": session_id,
            "target_stage": "stage_2",
            "reason": "tighten MVP scope",
        },
    )

    assert rollback_response.status_code == 200
    rolled_back = rollback_response.json()
    assert rolled_back["current_stage"] == "stage_2"
    assert "stage_2" not in rolled_back["approved_stages"]


def test_dispatch_api_rejects_invalid_rollback_target():
    client = make_client()
    session = client.post(
        "/sessions",
        json={"scenario": "dispatch_recommendation"},
    ).json()

    response = client.post(
        "/stages/rollback",
        json={
            "session_id": session["session_id"],
            "target_stage": "stage_4",
            "reason": "invalid direct rollback",
        },
    )

    assert response.status_code == 400
    assert "cannot roll back" in response.json()["detail"]["message"]


def test_approve_rejects_current_stage_before_run():
    client = make_client()
    session = client.post(
        "/sessions",
        json={"scenario": "dispatch_recommendation"},
    ).json()

    response = client.post("/stages/approve", json={"session_id": session["session_id"]})

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_stage_transition"
    assert "must be run before approval" in response.json()["detail"]["message"]


def test_report_is_gated_until_stage_4_is_run_and_approved():
    client = make_client()
    session = client.post(
        "/sessions",
        json={"scenario": "dispatch_recommendation"},
    ).json()
    session_id = session["session_id"]

    response = client.get(f"/reports/{session_id}")
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "report_not_ready"

    for _ in ["stage_1", "stage_2", "stage_3"]:
        assert client.post("/stages/run", json={"session_id": session_id}).status_code == 200
        assert client.post("/stages/approve", json={"session_id": session_id}).status_code == 200

    assert client.post("/stages/run", json={"session_id": session_id}).status_code == 200
    response = client.get(f"/reports/{session_id}")
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "report_not_ready"


def test_create_app_keeps_test_clients_isolated():
    first = make_client()
    second = make_client()
    session = first.post(
        "/sessions",
        json={"scenario": "dispatch_recommendation"},
    ).json()

    response = second.get(f"/sessions/{session['session_id']}")

    assert response.status_code == 404
