"""Deterministic verifier templates for the mock MVP."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.backend.core.config_loader import get_scenario_definition, get_stage_definition
from app.backend.schemas.common import Citation, DecisionItem, RiskItem
from app.backend.schemas.stage import StageOutputBundle
from app.backend.services.prd_packet_factory import build_demo_prd_packet, ready_prd_quality
from app.backend.services.scenario_profiles import get_scenario_profile

# Localized display text for verifier risk findings. verify() keeps English
# strings (tests assert keyword substrings); UI-facing RiskItems use Korean.
_RISK_DISPLAY_KO = {
    "Missing operational data sources for verification.": (
        "검증에 필요한 운영 데이터 소스가 없습니다."
    ),
    "Poor label quality makes the proposed model scope unreliable.": (
        "라벨 품질이 낮아 제안된 모델 범위의 신뢰도가 떨어집니다."
    ),
    "Scope may be too broad for a first MVP without baseline rules.": (
        "기준 규칙 없이는 첫 MVP 범위가 너무 넓을 수 있습니다."
    ),
}


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
            risks.append("Missing operational data sources for verification.")
            rollback_recommendation = "stage_1"

        if evidence.get("label_quality") == "poor":
            risks.append("Poor label quality makes the proposed model scope unreliable.")
            rollback_recommendation = "stage_2"

        mvp_scope = proposal.get("mvp_scope", [])
        scope_keywords = ["root_cause", "prediction", *get_scenario_profile(scenario)[
            "verify_scope_keywords"
        ]]
        if any(any(keyword in item for keyword in scope_keywords) for item in mvp_scope):
            risks.append("Scope may be too broad for a first MVP without baseline rules.")
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
        profile = get_scenario_profile(scenario)
        result = self.verify(scenario=scenario, proposal=proposal, evidence=evidence)

        risks = [
            RiskItem(
                category="data" if "data" in risk.lower() or "label" in risk.lower() else "scope",
                severity="medium",
                description=_RISK_DISPLAY_KO.get(risk, risk),
                mitigation="구현 전에 이전 단계의 가정을 다시 확인한다.",
            )
            for risk in result["risks"]
        ]
        if not risks:
            risks.append(
                RiskItem(
                    category="operational",
                    severity="low",
                    description=(
                        "규칙 우선 MVP 기준으로 운영 실현 가능성이 수용 가능한 수준이다."
                    ),
                    mitigation="첫 파일럿은 위험이 높은 구간으로 제한한다.",
                )
            )

        rollback_targets = list(stage_def.rollback_targets if stage_def else [])
        if (
            result["rollback_recommendation"]
            and result["rollback_recommendation"] not in rollback_targets
        ):
            rollback_targets.append(result["rollback_recommendation"])
        scenario_label = scenario_def.display_label if scenario_def else scenario
        status_label = "통과" if result["status"] == "pass" else "주의"
        summary = f"{scenario_label} 검증 상태: {status_label}."

        return StageOutputBundle(
            summary=summary,
            planner_view={
                "verifier_status": result["status"],
                "decision": (
                    "파일럿 진행"
                    if result["status"] == "pass"
                    else "범위를 좁힌 뒤 진행"
                ),
                "rollback_recommendation": result["rollback_recommendation"],
            },
            engineer_view={
                "checked_items": result["checked_items"],
                "required_data": evidence.get("data_sources", []),
                "implementation_guardrails": list(profile["verify_guardrails"]),
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
                    item="전면 최적화 이전에 MVP를 운영자 검토 추천 범위로 고정한다.",
                    status="proposed",
                    rationale=(
                        "이렇게 하면 확보 가능한 운영 데이터로 첫 파일럿을 검증할 수 있다."
                    ),
                )
            ],
            required_user_input=(
                []
                if result["status"] == "pass"
                else ["누락된 데이터 담당자와 파일럿 범위를 확정해주세요."]
            ),
            citations=citations or [],
            risks=risks,
            rollback_targets=rollback_targets,
        )
