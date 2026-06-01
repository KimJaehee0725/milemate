"""Microsoft Agent Framework graph boundary for milemate stages."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from typing import Any, Callable, Dict, List, Optional

from app.backend.integrations.codex_client import CodexClient
from app.backend.schemas.common import Citation, RiskItem
from app.backend.schemas.session import SessionState
from app.backend.schemas.stage import StageOutputBundle
from app.backend.services.planner_service import PlannerService
from app.backend.services.report_service import ReportService
from app.backend.services.verifier_service import VerifierService


@dataclass(frozen=True)
class AgentGraphInput:
    session: SessionState
    stage_id: str
    user_input: str
    context: Dict[str, Any]
    citations: List[Citation]
    approved_state: Dict[str, Any]
    proposal_state: Dict[str, Any]
    evidence_state: Dict[str, Any]
    collected_risks: List[RiskItem]


StageNode = Callable[[AgentGraphInput], StageOutputBundle]


class MilemateAgentGraphRunner:
    """MAF-ready stage graph adapter with deterministic demo nodes."""

    def __init__(
        self,
        planner: Optional[PlannerService] = None,
        verifier: Optional[VerifierService] = None,
        reporter: Optional[ReportService] = None,
        codex_client: Optional[CodexClient] = None,
        use_codex: bool = False,
    ) -> None:
        self.planner = planner or PlannerService()
        self.verifier = verifier or VerifierService()
        self.reporter = reporter or ReportService()
        self.codex_client = codex_client
        self.use_codex = use_codex
        self.framework_available = find_spec("agent_framework") is not None
        self.nodes: Dict[str, StageNode] = {
            "stage_1": self._planner_node,
            "stage_2": self._planner_node,
            "stage_3": self._verifier_node,
            "stage_4": self._report_node,
        }

    def run(self, graph_input: AgentGraphInput) -> StageOutputBundle:
        node = self.nodes.get(graph_input.stage_id)
        if node is None:
            raise ValueError(f"unsupported stage: {graph_input.stage_id}")
        output = node(graph_input)
        if self.use_codex and self.codex_client is not None:
            output.engineer_view["codex_note"] = self.codex_client.generate_stage_text(
                stage_id=graph_input.stage_id,
                scenario=graph_input.session.scenario,
                user_input=graph_input.user_input,
                context=graph_input.context,
            )
        output.engineer_view["graph_runtime"] = (
            "microsoft_agent_framework_core"
            if self.framework_available
            else "deterministic_graph_adapter"
        )
        return output

    def _planner_node(self, graph_input: AgentGraphInput) -> StageOutputBundle:
        return self.planner.build_stage_output(
            stage_id=graph_input.stage_id,
            scenario=graph_input.session.scenario,
            user_input=graph_input.user_input
            or str(graph_input.session.metadata.get("user_input", "")),
            citations=graph_input.citations,
        )

    def _verifier_node(self, graph_input: AgentGraphInput) -> StageOutputBundle:
        return self.verifier.build_stage_output(
            scenario=graph_input.session.scenario,
            proposal=graph_input.proposal_state,
            evidence=graph_input.evidence_state,
            citations=graph_input.citations,
        )

    def _report_node(self, graph_input: AgentGraphInput) -> StageOutputBundle:
        return self.reporter.build_stage_output(
            scenario=graph_input.session.scenario,
            approved_state=graph_input.approved_state,
            citations=graph_input.citations,
            risks=graph_input.collected_risks,
        )
