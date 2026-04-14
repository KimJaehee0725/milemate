import pytest


@pytest.mark.xfail(reason="ReportService contract not implemented yet")
def test_report_service_builds_planner_and_engineer_outputs():
    from app.backend.services.report_service import ReportService

    service = ReportService()
    result = service.build_reports(
        scenario="dispatch_recommendation",
        approved_state={
            "problem_summary": "peak-time dispatch bottleneck",
            "mvp_scope": ["dashboard", "priority_recommendation"],
        },
    )

    assert "planner_report" in result
    assert "engineer_report" in result
    assert "decision_log" in result


@pytest.mark.xfail(reason="Planner report structure not implemented yet")
def test_planner_report_contains_required_sections():
    from app.backend.services.report_service import ReportService

    service = ReportService()
    result = service.build_reports(
        scenario="eta_prediction",
        approved_state={"problem_summary": "eta communication problem"},
    )

    report = result["planner_report"]
    for key in ["problem_redefinition", "target_users", "prioritized_kpis", "mvp_scope"]:
        assert key in report


@pytest.mark.xfail(reason="Engineer report structure not implemented yet")
def test_engineer_report_contains_required_sections():
    from app.backend.services.report_service import ReportService

    service = ReportService()
    result = service.build_reports(
        scenario="failed_delivery_risk",
        approved_state={"problem_summary": "failed delivery risk"},
    )

    report = result["engineer_report"]
    for key in ["required_data", "required_tech_blocks", "constraints", "verification_plan"]:
        assert key in report
