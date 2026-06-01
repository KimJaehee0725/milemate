"""Deterministic PRD packet quality checks."""

from __future__ import annotations

from typing import Iterable, List

from app.backend.schemas.common import Citation
from app.backend.schemas.stage import PrdPacket, PrdQualityReport


class PrdPacketVerifier:
    """Check whether a generated PRD is ready for a planner/developer meeting."""

    def evaluate(
        self,
        packet: PrdPacket,
        citations: Iterable[Citation] | None = None,
        *,
        repair_attempted: bool = False,
        require_external_url: bool = False,
    ) -> PrdQualityReport:
        checks = [
            (
                self._problem_is_complete(packet),
                "문제 정의에 고객 문제, 사업 영향, 현재 우회 방식, 성공 기준이 모두 필요합니다.",
            ),
            (
                self._screens_are_complete(packet),
                "최소 1개 화면 명세에 주요 액션과 인수 기준이 필요합니다.",
            ),
            (
                bool(packet.policies),
                "최소 1개 이상의 운영/서비스 정책 규칙이 필요합니다.",
            ),
            (
                self._metrics_are_complete(packet),
                "최소 2개 KPI에 현재 기준, 목표 기준, 측정 방식이 필요합니다.",
            ),
            (
                len(packet.data_requirements) >= 3,
                "최소 3개 이상의 데이터 요구사항이 필요합니다.",
            ),
            (
                len(packet.event_logs) >= 2,
                "최소 2개 이상의 이벤트 로그 정의가 필요합니다.",
            ),
            (
                bool(packet.implementation_slices),
                "개발자가 착수할 구현 단위가 필요합니다.",
            ),
            (
                bool(packet.decision_agenda),
                "회의에서 결정할 안건과 담당자가 필요합니다.",
            ),
            (
                bool(packet.developer_handoff),
                "개발 회의용 전달사항이 필요합니다.",
            ),
        ]
        if require_external_url:
            checks.append(
                (
                    self._has_url_evidence(packet, citations or []),
                    "외부 자료 링크가 포함된 근거 citation이 최소 1개 필요합니다.",
                )
            )

        findings = [message for passed, message in checks if not passed]
        score = round(((len(checks) - len(findings)) / len(checks)) * 100)
        return PrdQualityReport(
            status="ready" if not findings else "needs_review",
            score=score,
            findings=findings,
            repair_attempted=repair_attempted,
        )

    @staticmethod
    def _problem_is_complete(packet: PrdPacket) -> bool:
        problem = packet.problem
        return all(
            [
                problem.customer_pain.strip(),
                problem.business_impact.strip(),
                problem.current_workaround.strip(),
                problem.success_criteria,
            ]
        )

    @staticmethod
    def _screens_are_complete(packet: PrdPacket) -> bool:
        if not packet.screens:
            return False
        return all(
            screen.name.strip()
            and screen.primary_actions
            and screen.acceptance_criteria
            for screen in packet.screens
        )

    @staticmethod
    def _metrics_are_complete(packet: PrdPacket) -> bool:
        complete_metrics = [
            metric
            for metric in packet.metrics
            if metric.name.strip()
            and metric.baseline.strip()
            and metric.target.strip()
            and metric.measurement.strip()
        ]
        return len(complete_metrics) >= 2

    @staticmethod
    def _has_url_evidence(
        packet: PrdPacket,
        citations: Iterable[Citation],
    ) -> bool:
        evidence: List[Citation] = [*packet.evidence_links, *citations]
        return any(
            item.locator.startswith("https://") or item.locator.startswith("http://")
            for item in evidence
        )
