"""Deterministic verifier templates for the mock MVP."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.backend.core.config_loader import get_scenario_definition, get_stage_definition
from app.backend.schemas.common import Citation, DecisionItem, RiskItem
from app.backend.schemas.stage import StageOutputBundle


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
        if any("root_cause" in item or "prediction" in item for item in mvp_scope):
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
                        "Operational feasibility is acceptable for a rule-first dispatch MVP."
                    ),
                    mitigation="Keep the first pilot limited to high-delay zones.",
                )
            )

        rollback_targets = list(stage_def.rollback_targets if stage_def else [])
        if (
            result["rollback_recommendation"]
            and result["rollback_recommendation"] not in rollback_targets
        ):
            rollback_targets.append(result["rollback_recommendation"])

        return StageOutputBundle(
            summary=(
                f"Verification status is {result['status']} for "
                f"{scenario_def.label if scenario_def else scenario}."
            ),
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
                    "start with rules and ranked recommendations",
                    "log dispatcher overrides",
                    "monitor delay and workload balance daily",
                ],
            },
            decision_points=[
                DecisionItem(
                    item="Lock MVP to dispatch recommendations before full route optimization.",
                    status="proposed",
                    rationale=(
                        "This keeps the first pilot verifiable with available operations data."
                    ),
                )
            ],
            required_user_input=(
                []
                if result["status"] == "pass"
                else ["Confirm missing data owner and pilot zone."]
            ),
            citations=citations or [],
            risks=risks,
            rollback_targets=rollback_targets,
        )
