"""In-process backend for Streamlit smoke tests and offline demos."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from app.backend.core.agent_graph import MilemateAgentGraphRunner
from app.backend.core.orchestrator import Orchestrator
from app.backend.core.stage_manager import StageManager, StageTransitionError
from app.backend.schemas.stage import StageOutputBundle
from app.backend.services.planner_service import PlannerService
from app.backend.services.report_export_service import ReportExportService
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


class ReplayCodexClient:
    """Replays previously captured stage outputs (from a real codex run) so a live
    demo can show the full-quality result instantly instead of waiting ~20 minutes.

    Activated by env var MILEMATE_REPLAY=<path to capture json>. For any scenario or
    stage not present in the capture it falls back to LocalFakeCodexClient, so other
    scenarios still work offline.
    """

    def __init__(self, capture_paths, fallback=None) -> None:
        if isinstance(capture_paths, (str, Path)):
            capture_paths = [capture_paths]
        # map: (scenario, stage_id) -> captured StageOutputBundle dict
        self.by_key: Dict[tuple, Dict[str, Any]] = {}
        self.scenarios = set()
        for cp in capture_paths:
            data = json.loads(Path(cp).read_text(encoding="utf-8"))
            scn = data.get("scenario")
            self.scenarios.add(scn)
            for st in data.get("stages", []):
                self.by_key[(scn, st["stage_id"])] = st["output"]
        self.fallback = fallback or LocalFakeCodexClient()

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
        captured = self.by_key.get((scenario, stage_id))
        if captured is not None:
            return StageOutputBundle.model_validate(captured)
        return self.fallback.generate_stage_output(
            stage_id=stage_id,
            scenario=scenario,
            user_input=user_input,
            context=context,
            citations=citations,
            approved_state=approved_state,
            proposal_state=proposal_state,
            evidence_state=evidence_state,
            collected_risks=collected_risks,
            rollback_targets=rollback_targets,
            scenario_metadata=scenario_metadata,
        )


class DemoCodexClient:
    """Switches per request between pre-generated replay and a real (live) codex
    call, based on context['gen_mode'] ('replay' default, or 'live'). The live
    client is constructed lazily so the offline demo never touches the codex CLI
    unless live generation is explicitly chosen.
    """

    def __init__(self, capture_paths) -> None:
        self.replay = ReplayCodexClient(capture_paths)
        self._live = None

    def _live_client(self):
        if self._live is None:
            from app.backend.core.config_loader import get_model_runtime_config
            from app.backend.integrations.codex_client import CodexClient

            self._live = CodexClient(runtime_config=get_model_runtime_config())
        return self._live

    def generate_stage_output(self, **kwargs):
        mode = str((kwargs.get("context") or {}).get("gen_mode", "replay"))
        client = self._live_client() if mode == "live" else self.replay
        return client.generate_stage_output(**kwargs)


def _build_codex_client():
    """DemoCodexClient (replay + optional live) when MILEMATE_REPLAY is set,
    else the offline fake."""
    replay = os.getenv("MILEMATE_REPLAY", "").strip()
    if replay:
        paths = [p.strip() for p in replay.split(os.pathsep) if p.strip()]
        return DemoCodexClient(paths)
    return LocalFakeCodexClient()


class LocalDemoAPI:
    """Tiny endpoint-shaped adapter around the backend runtime."""

    def __init__(self) -> None:
        self.stage_manager = StageManager()
        self.orchestrator = Orchestrator(
            stage_manager=self.stage_manager,
            graph_runner=MilemateAgentGraphRunner(codex_client=_build_codex_client()),
        )
        self.report_exporter = ReportExportService()

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

    def binary_request(self, method: str, path: str) -> bytes:
        try:
            if method == "GET" and "/reports/" in path and "/exports/" in path:
                report_path, export_format = path.rsplit("/exports/", 1)
                session_id = report_path.rsplit("/", 1)[-1]
                report = self.orchestrator.build_final_report(session_id)
                return self.report_exporter.export(report, export_format).content
        except StageTransitionError as exc:
            raise RuntimeError(str(exc)) from exc
        raise RuntimeError(f"unsupported local demo binary request: {method} {path}")
