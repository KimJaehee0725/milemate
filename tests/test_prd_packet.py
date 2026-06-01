from app.backend.schemas.common import Citation
from app.backend.schemas.stage import PrdPacket
from app.backend.services.prd_packet_factory import build_demo_prd_packet
from app.backend.services.prd_packet_verifier import PrdPacketVerifier


def test_prd_packet_verifier_passes_complete_packet_with_url_evidence():
    citation = Citation(
        source_type="industry_cases",
        title="External reference",
        locator="https://example.com/reference",
        relevance_note="supports the meeting packet",
    )
    packet = build_demo_prd_packet(
        stage_id="stage_1",
        scenario="dispatch_recommendation",
        summary="테스트 PRD",
        citations=[citation],
    )

    quality = PrdPacketVerifier().evaluate(
        packet,
        [citation],
        require_external_url=True,
    )

    assert quality.status == "ready"
    assert quality.score == 100
    assert quality.findings == []


def test_prd_packet_verifier_flags_missing_meeting_requirements():
    quality = PrdPacketVerifier().evaluate(
        PrdPacket(),
        [],
        require_external_url=True,
    )

    assert quality.status == "needs_review"
    assert "화면 명세" in " ".join(quality.findings)
    assert "외부 자료 링크" in " ".join(quality.findings)
