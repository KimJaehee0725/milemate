from io import BytesIO
from zipfile import ZipFile


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


def test_report_document_model_preserves_business_sections():
    from app.backend.services.report_export_service import ReportExportService
    from app.backend.services.report_service import ReportService

    report = ReportService().build_reports(
        scenario="dispatch_recommendation",
        approved_state={
            "problem_summary": "긴 한국어 아이디어를 회사 보고서로 정리해야 합니다.",
            "mvp_scope": ["운영자 승인형 추천", "데이터 소유자 확인"],
        },
    )

    document = ReportExportService().build_document_model(report)

    assert document.title == "Milemate 최종 기획서"
    assert any(section.title == "문제 정의" for section in document.sections)
    assert any(section.title == "개발팀 확인사항" for section in document.sections)
    assert any(card.title == "핵심 리스크" for card in document.cards)


def test_report_export_service_builds_docx_pdf_and_pptx_bytes():
    from app.backend.services.report_export_service import ReportExportService
    from app.backend.services.report_service import ReportService

    report = ReportService().build_reports(
        scenario="eta_prediction",
        approved_state={"problem_summary": "ETA 안내 기획서를 문서 패키지로 내보냅니다."},
        risks=[
            {
                "category": "data",
                "severity": "high",
                "description": "실시간 위치 데이터가 늦게 들어옵니다.",
                "mitigation": "데이터 최신성 기준을 먼저 확정합니다.",
            }
        ],
    )
    exporter = ReportExportService()

    pdf = exporter.export(report, "pdf")
    docx = exporter.export(report, "docx")
    pptx = exporter.export(report, "pptx")

    assert pdf.content.startswith(b"%PDF")
    assert docx.content.startswith(b"PK")
    assert pptx.content.startswith(b"PK")

    with ZipFile(BytesIO(docx.content)) as package:
        assert "word/document.xml" in package.namelist()
    with ZipFile(BytesIO(pptx.content)) as package:
        assert "ppt/presentation.xml" in package.namelist()
