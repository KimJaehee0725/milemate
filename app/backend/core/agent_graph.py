"""Stage graph boundary for milemate Codex generation."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from typing import Any, Callable, Dict, List, Optional, Protocol

from app.backend.core.config_loader import get_stage_definition
from app.backend.integrations.codex_client import CodexClient
from app.backend.schemas.common import Citation, RiskItem
from app.backend.schemas.session import SessionState
from app.backend.schemas.stage import StageOutputBundle


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


class StageGenerationClient(Protocol):
    def generate_stage_output(
        self,
        stage_id: str,
        scenario: str,
        user_input: str,
        context: Dict[str, Any],
        citations: List[Citation],
        approved_state: Dict[str, Any],
        proposal_state: Dict[str, Any],
        evidence_state: Dict[str, Any],
        collected_risks: List[RiskItem],
        rollback_targets: List[str],
        scenario_metadata: Dict[str, Any],
    ) -> StageOutputBundle:
        ...


StageNode = Callable[[AgentGraphInput], StageOutputBundle]


class MilemateAgentGraphRunner:
    """MAF-ready stage graph adapter that uses Codex for stage generation."""

    def __init__(
        self,
        codex_client: Optional[StageGenerationClient] = None,
    ) -> None:
        self.codex_client = codex_client or CodexClient()
        self.framework_available = find_spec("agent_framework") is not None
        self.nodes: Dict[str, StageNode] = {
            "stage_1": self._codex_node,
            "stage_2": self._codex_node,
            "stage_3": self._codex_node,
            "stage_4": self._codex_node,
        }

    def run(self, graph_input: AgentGraphInput) -> StageOutputBundle:
        node = self.nodes.get(graph_input.stage_id)
        if node is None:
            raise ValueError(f"unsupported stage: {graph_input.stage_id}")
        return node(graph_input)

    def _codex_node(self, graph_input: AgentGraphInput) -> StageOutputBundle:
        stage_def = get_stage_definition(graph_input.stage_id)
        rollback_targets = list(stage_def.rollback_targets if stage_def else [])
        output = self.codex_client.generate_stage_output(
            stage_id=graph_input.stage_id,
            scenario=graph_input.session.scenario,
            user_input=graph_input.user_input
            or str(graph_input.session.metadata.get("user_input", "")),
            context=graph_input.context,
            citations=graph_input.citations,
            approved_state=graph_input.approved_state,
            proposal_state=graph_input.proposal_state,
            evidence_state=graph_input.evidence_state,
            collected_risks=graph_input.collected_risks,
            rollback_targets=rollback_targets,
            scenario_metadata=dict(graph_input.session.metadata),
        )
        engineer_view = {
            **output.engineer_view,
            "graph_runtime": (
                "microsoft_agent_framework_core"
                if self.framework_available
                else "openai_codex_responses"
            ),
        }
        citations = output.citations or graph_input.citations
        return output.model_copy(
            update={
                "engineer_view": engineer_view,
                "citations": citations,
                "rollback_targets": rollback_targets,
            }
        )
