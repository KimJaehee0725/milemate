"""In-process backend for Streamlit smoke tests and offline demos."""

from __future__ import annotations

from typing import Any, Dict

from app.backend.core.orchestrator import Orchestrator
from app.backend.core.stage_manager import StageManager, StageTransitionError


class LocalDemoAPI:
    """Tiny endpoint-shaped adapter around the backend runtime."""

    def __init__(self) -> None:
        self.stage_manager = StageManager()
        self.orchestrator = Orchestrator(stage_manager=self.stage_manager)

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
