def test_verifier_returns_structured_result_for_stage_3_review():
    from app.backend.services.verifier_service import VerifierService

    service = VerifierService()
    result = service.verify(
        scenario="dispatch_recommendation",
        proposal={"mvp_scope": ["dashboard", "risk_orders_only"]},
        evidence={"data_sources": ["orders", "courier_locations"]},
    )

    assert "status" in result
    assert "risks" in result
    assert "rollback_recommendation" in result


def test_verifier_flags_missing_data_as_risk():
    from app.backend.services.verifier_service import VerifierService

    service = VerifierService()
    result = service.verify(
        scenario="eta_prediction",
        proposal={"mvp_scope": ["eta_dashboard"]},
        evidence={"data_sources": []},
    )

    assert result["status"] in {"warning", "fail"}
    assert any("data" in r.lower() for r in result["risks"])


def test_verifier_can_recommend_rollback_to_previous_stage():
    from app.backend.services.verifier_service import VerifierService

    service = VerifierService()
    result = service.verify(
        scenario="failed_delivery_risk",
        proposal={"mvp_scope": ["root_cause_prediction"]},
        evidence={"label_quality": "poor"},
    )

    assert result["rollback_recommendation"] in {"stage_1", "stage_2", None}
