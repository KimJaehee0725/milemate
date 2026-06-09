"""Deterministic verifier templates for the mock MVP."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.backend.core.config_loader import get_scenario_definition, get_stage_definition
from app.backend.schemas.common import Citation, DecisionItem, RiskItem
from app.backend.schemas.stage import StageOutputBundle
from app.backend.services.prd_packet_factory import build_demo_prd_packet, ready_prd_quality


class VerifierService:
    """Evaluate proposal feasibility with deterministic rules."""

    def verify(
        self,
        scenario: str,
        proposal: Dict[str, Any],
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        risks: List[str] = []
        rollback_recommendation: Optional[str] = None

        data_sources = evidence.get("data_sources")
        if data_sources == []:
            risks.append("기획서 검증에 필요한 운영/사용자 data 출처가 비어 있습니다.")
            rollback_recommendation = "stage_1"

        if evidence.get("label_quality") == "poor":
            risks.append("데이터 품질이 낮아 제안한 MVP 범위를 그대로 신뢰하기 어렵습니다.")
            rollback_recommendation = "stage_2"

        mvp_scope = proposal.get("mvp_scope", [])
        if any("root_cause" in item or "prediction" in item for item in mvp_scope):
            risks.append("현재 기준선 없이 첫 MVP 범위가 과도하게 넓어질 수 있습니다.")
            rollback_recommendation = rollback_recommendation or "stage_2"

        if risks and any("Missing" in risk or "Poor" in risk for risk in risks):
            status = "warning"
        elif risks:
            status = "warning"
        else:
            status = "pass"

        return {
            "status": status,
            "risks": risks,
            "rollback_recommendation": rollback_recommendation,
            "checked_items": [
                "data availability",
                "MVP scope realism",
                "operational handoff",
                "regulatory exposure",
            ],
        }

    def build_stage_output(
        self,
        scenario: str,
        proposal: Dict[str, Any],
        evidence: Dict[str, Any],
        citations: Optional[List[Citation]] = None,
    ) -> StageOutputBundle:
        scenario_def = get_scenario_definition(scenario)
        stage_def = get_stage_definition("stage_3")
        result = self.verify(scenario=scenario, proposal=proposal, evidence=evidence)

        risks = [
            RiskItem(
                category="data" if "data" in risk.lower() or "label" in risk.lower() else "scope",
                severity="medium",
                description=risk,
                mitigation="Reconfirm the previous stage assumptions before implementation.",
            )
            for risk in result["risks"]
        ]
        if not risks:
            risks.append(
                RiskItem(
                    category="operational",
                    severity="low",
                    description=(
                        "기획서 수준의 첫 MVP 검토에는 운영 실현 가능성이 수용 가능합니다."
                    ),
                    mitigation="첫 파일럿은 설명 가능한 범위와 명확한 KPI로 제한합니다.",
                )
            )

        rollback_targets = list(stage_def.rollback_targets if stage_def else [])
        if (
            result["rollback_recommendation"]
            and result["rollback_recommendation"] not in rollback_targets
        ):
            rollback_targets.append(result["rollback_recommendation"])
        summary = (
            f"Verification status is {result['status']} for "
            f"{scenario_def.label if scenario_def else scenario}."
        )

        return StageOutputBundle(
            summary=summary,
            planner_view={
                "verifier_status": result["status"],
                "decision": (
                    "Proceed with pilot"
                    if result["status"] == "pass"
                    else "Proceed after tightening scope"
                ),
                "rollback_recommendation": result["rollback_recommendation"],
            },
            engineer_view={
                "checked_items": result["checked_items"],
                "required_data": evidence.get("data_sources", []),
                "implementation_guardrails": [
                    "기획자 승인 가능한 범위부터 시작",
                    "승인/보류/롤백 사유를 기록",
                    "KPI와 데이터 품질을 단계별로 확인",
                ],
            },
            prd_packet=build_demo_prd_packet(
                stage_id="stage_3",
                scenario=scenario,
                summary=summary,
                citations=citations or [],
                evidence=evidence,
            ),
            prd_quality=ready_prd_quality(),
            decision_points=[
                DecisionItem(
                    item="첫 MVP는 설명 가능한 기획서 범위와 리스크 검토 흐름으로 제한합니다.",
                    status="proposed",
                    rationale=(
                        "비개발 기획자가 개발팀에 전달할 수 있는 근거와 "
                        "보류 조건을 먼저 확보합니다."
                    ),
                )
            ],
            required_user_input=(
                []
                if result["status"] == "pass"
                else ["부족한 데이터의 담당자와 첫 파일럿 KPI를 확인해야 합니다."]
            ),
            citations=citations or [],
            risks=risks,
            rollback_targets=rollback_targets,
        )
