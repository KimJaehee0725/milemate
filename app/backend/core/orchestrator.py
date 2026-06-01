"""Internal workflow entrypoint for the mock MVP."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.backend.core.agent_graph import AgentGraphInput, MilemateAgentGraphRunner
from app.backend.integrations.legal_adapter import LegalAdapter
from app.backend.integrations.retrieval_adapter import RetrievalAdapter
from app.backend.schemas.common import Citation, ErrorCode, RiskItem, StageRunStatus
from app.backend.schemas.report import FinalReportBundle
from app.backend.schemas.stage import StageResponse
from app.backend.services.planner_service import PlannerService
from app.backend.services.report_service import ReportService
from app.backend.services.verifier_service import VerifierService

from .stage_manager import StageManager, StageTransitionError


class Orchestrator:
    """Run the stage workflow through the graph runner boundary."""

    def __init__(
        self,
        stage_manager: Optional[StageManager] = None,
        planner: Optional[PlannerService] = None,
        verifier: Optional[VerifierService] = None,
        reporter: Optional[ReportService] = None,
        retrieval: Optional[RetrievalAdapter] = None,
        legal: Optional[LegalAdapter] = None,
        model_client: Optional[object] = None,
        graph_runner: Optional[MilemateAgentGraphRunner] = None,
    ) -> None:
        self.stage_manager = stage_manager or StageManager()
        self.planner = planner or PlannerService()
        self.verifier = verifier or VerifierService()
        self.reporter = reporter or ReportService()
        self.retrieval = retrieval or RetrievalAdapter()
        self.legal = legal or LegalAdapter()
        self.model_client = model_client
        self.graph_runner = graph_runner or MilemateAgentGraphRunner(
            planner=self.planner,
            verifier=self.verifier,
            reporter=self.reporter,
        )

    def run_current_stage(
        self,
        session_id: str,
        user_input: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> StageResponse:
        session = self.stage_manager.get_session(session_id)
        stage_id = session.current_stage
        context = context or {}
        citations = self._citations(session.scenario, stage_id)
        output = self.graph_runner.run(
            AgentGraphInput(
                session=session,
                stage_id=stage_id,
                user_input=user_input,
                context=context,
                citations=citations,
                approved_state=self._approved_state(session),
                proposal_state=self._proposal_state(session),
                evidence_state=self._evidence_state(session, context),
                collected_risks=self._collected_risks(session),
            )
        )
        response = StageResponse(
            session_id=session.session_id,
            stage_id=stage_id,
            status=StageRunStatus.COMPLETED,
            output=output,
        )
        self.stage_manager.store_stage_response(session, response)
        return response

    def approve_current_stage(self, session_id: str, stage_id: Optional[str] = None):
        session = self.stage_manager.approve_stage(session_id, stage_id)
        if not self.stage_manager.is_final_stage(session.current_stage):
            session = self.stage_manager.advance_stage(session)
        return session

    def rollback(self, session_id: str, target_stage: str, reason: str = ""):
        return self.stage_manager.rollback_to(session_id, target_stage, reason=reason)

    def build_final_report(self, session_id: str) -> FinalReportBundle:
        session = self.stage_manager.get_session(session_id)
        if "stage_4" not in session.stage_outputs:
            raise StageTransitionError(
                "stage_4 must be run before final report is available",
                ErrorCode.REPORT_NOT_READY,
            )
        if "stage_4" not in session.approved_stages:
            raise StageTransitionError(
                "stage_4 must be approved before final report is available",
                ErrorCode.REPORT_NOT_READY,
            )

        output = session.stage_outputs["stage_4"]
        return FinalReportBundle.model_validate(
            {
                "planner_report": output.get("planner_view", {}),
                "engineer_report": output.get("engineer_view", {}),
                "decision_log": output.get("decision_points", []),
                "citations": output.get("citations", []),
                "risks": output.get("risks", []),
            }
        )

    def _citations(self, scenario: str, stage_id: str) -> List[Citation]:
        query = f"{scenario} {stage_id} last-mile planning"
        source_type = "industry_cases" if stage_id == "stage_1" else "technical_docs"
        results = self.retrieval.search(
            query=query,
            source_type=source_type,
            scenario=scenario,
            top_k=1,
        )
        citations = [Citation.model_validate(item) for item in results]
        if stage_id in {"stage_3", "stage_4"}:
            citations.extend(
                Citation.model_validate(item)
                for item in self.legal.search("위치정보 배송 배차")
            )
        return citations

    @staticmethod
    def _stage_output(session, stage_id: str) -> Dict[str, Any]:
        return session.stage_outputs.get(stage_id, {})

    def _approved_state(self, session) -> Dict[str, Any]:
        state: Dict[str, Any] = {}
        stage_1 = self._stage_output(session, "stage_1").get("planner_view", {})
        stage_2_planner = self._stage_output(session, "stage_2").get("planner_view", {})
        stage_2_engineer = self._stage_output(session, "stage_2").get("engineer_view", {})

        if "problem_summary" in stage_1:
            state["problem_summary"] = stage_1["problem_summary"]
        if "mvp_in_scope" in stage_2_planner:
            state["mvp_scope"] = stage_2_planner["mvp_in_scope"]
        elif "mvp_scope" in stage_2_engineer:
            state["mvp_scope"] = stage_2_engineer["mvp_scope"]
        return state

    def _proposal_state(self, session) -> Dict[str, Any]:
        state = self._approved_state(session)
        state.setdefault("mvp_scope", ["dashboard", "risk_orders_only"])
        return state

    def _evidence_state(self, session, context: Dict[str, Any]) -> Dict[str, Any]:
        if context:
            return context
        scenario_def = self.stage_manager.config.scenarios.scenarios.get(session.scenario)
        return {"data_sources": list(scenario_def.core_data if scenario_def else [])}

    def _collected_risks(self, session) -> List[RiskItem]:
        risks: List[RiskItem] = []
        for output in session.stage_outputs.values():
            risks.extend(RiskItem.model_validate(item) for item in output.get("risks", []))
        return risks
