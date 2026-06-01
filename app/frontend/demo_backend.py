"""In-process backend for Streamlit smoke tests and offline demos."""

from __future__ import annotations

from typing import Any, Dict

from app.backend.core.agent_graph import MilemateAgentGraphRunner
from app.backend.core.orchestrator import Orchestrator
from app.backend.core.stage_manager import StageManager, StageTransitionError
from app.backend.services.planner_service import PlannerService
from app.backend.services.report_service import ReportService
from app.backend.services.verifier_service import VerifierService


class LocalFakeCodexClient:
    """Explicit no-network Codex substitute for Streamlit local demos and AppTest."""

    def __init__(self) -> None:
        self.planner = PlannerService()
        self.verifier = VerifierService()
        self.reporter = ReportService()

    def generate_stage_output(
        self,
        stage_id,
        scenario,
        user_input,
        context,
        citations,
        approved_state,
        proposal_state,
        evidence_state,
        collected_risks,
        rollback_targets,
        scenario_metadata,
    ):
        if stage_id in {"stage_1", "stage_2"}:
            return self.planner.build_stage_output(
                stage_id=stage_id,
                scenario=scenario,
                user_input=user_input,
                citations=citations,
            )
        if stage_id == "stage_3":
            return self.verifier.build_stage_output(
                scenario=scenario,
                proposal=proposal_state,
                evidence=evidence_state,
                citations=citations,
            )
        if stage_id == "stage_4":
            return self.reporter.build_stage_output(
                scenario=scenario,
                approved_state=approved_state,
                citations=citations,
                risks=collected_risks,
            )
        raise ValueError(f"unsupported stage: {stage_id}")


class LocalDemoAPI:
    """Tiny endpoint-shaped adapter around the backend runtime."""

    def __init__(self) -> None:
        self.stage_manager = StageManager()
        self.orchestrator = Orchestrator(
            stage_manager=self.stage_manager,
            graph_runner=MilemateAgentGraphRunner(codex_client=LocalFakeCodexClient()),
        )

    def request(
        self,
        method: str,
        path: str,
        payload: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        payload = payload or {}
        try:
            if method == "POST" and path == "/sessions":
                return self.stage_manager.create_session(
                    scenario=str(payload.get("scenario", "dispatch_recommendation")),
                    user_input=str(payload.get("user_input", "")),
                    metadata=dict(payload.get("metadata", {})),
                ).model_dump(mode="json")
            if method == "GET" and path.startswith("/sessions/"):
                session_id = path.rsplit("/", 1)[-1]
                return self.stage_manager.get_session(session_id).model_dump(mode="json")
            if method == "POST" and path == "/stages/run":
                return self.orchestrator.run_current_stage(
                    session_id=str(payload["session_id"]),
                    user_input=str(payload.get("user_input", "")),
                    context=dict(payload.get("context", {})),
                ).model_dump(mode="json")
            if method == "POST" and path == "/stages/approve":
                return self.orchestrator.approve_current_stage(
                    session_id=str(payload["session_id"]),
                    stage_id=payload.get("stage_id"),
                ).model_dump(mode="json")
            if method == "POST" and path == "/stages/rollback":
                return self.orchestrator.rollback(
                    session_id=str(payload["session_id"]),
                    target_stage=str(payload["target_stage"]),
                    reason=str(payload.get("reason", "")),
                ).model_dump(mode="json")
            if method == "GET" and path.startswith("/reports/"):
                session_id = path.rsplit("/", 1)[-1]
                return self.orchestrator.build_final_report(session_id).model_dump(mode="json")
        except StageTransitionError as exc:
            raise RuntimeError(str(exc)) from exc
        raise RuntimeError(f"unsupported local demo request: {method} {path}")
