"""Stage state manager for the mock MVP workflow."""

from __future__ import annotations

from typing import Dict, Iterable, Optional
from uuid import uuid4

from app.backend.core.config_loader import RootConfig, load_app_config
from app.backend.core.rollback_manager import RollbackManager
from app.backend.core.session_store import InMemorySessionStore, SessionStore
from app.backend.schemas.common import ErrorCode, StageRunStatus
from app.backend.schemas.session import SessionState, StageStatus
from app.backend.schemas.stage import StageResponse


class StageTransitionError(ValueError):
    """Raised when a stage transition violates the configured workflow."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INVALID_STAGE_TRANSITION,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code


class StageManager:
    """Manage stage sessions using YAML stage/scenario definitions.

    The manager owns transition rules while persistence is delegated to a
    SessionStore implementation.
    """

    def __init__(
        self,
        config: Optional[RootConfig] = None,
        store: Optional[SessionStore] = None,
        rollback_manager: Optional[RollbackManager] = None,
    ) -> None:
        self.config = config or load_app_config()
        self.store = store or InMemorySessionStore()
        self.rollback_manager = rollback_manager or RollbackManager()
        self._stage_order = [stage.id for stage in self.config.stages.stages]
        self._stage_by_id = self.config.stages.by_id()

    def create_session(
        self,
        scenario: str,
        user_input: str = "",
        metadata: Optional[Dict[str, object]] = None,
    ) -> SessionState:
        if scenario not in self.config.scenarios.scenarios:
            raise StageTransitionError(
                f"unknown scenario: {scenario}",
                ErrorCode.UNKNOWN_SCENARIO,
            )
        if not self._stage_order:
            raise StageTransitionError("no stages are configured")

        initial_stage = self._stage_order[0]
        session = SessionState(
            session_id=str(uuid4()),
            scenario=scenario,
            current_stage=initial_stage,
            stage_history=[StageStatus(stage_id=initial_stage)],
            metadata={
                "user_input": user_input,
                **(metadata or {}),
            },
        )
        return self.store.save(session)

    def get_session(self, session_id: str) -> SessionState:
        try:
            return self.store.get(session_id)
        except KeyError as exc:
            raise StageTransitionError(
                f"session not found: {session_id}",
                ErrorCode.UNKNOWN_SESSION,
            ) from exc

    def approve_stage(
        self,
        session_or_id: SessionState | str,
        stage_id: Optional[str] = None,
    ) -> SessionState:
        session = self._resolve_session(session_or_id)
        approved_stage = stage_id or session.current_stage
        if approved_stage != session.current_stage:
            raise StageTransitionError(
                f"cannot approve {approved_stage}; current stage is {session.current_stage}"
            )
        if approved_stage not in session.stage_outputs:
            raise StageTransitionError(
                f"{approved_stage} must be run before approval"
            )
        if approved_stage not in session.approved_stages:
            session.approved_stages.append(approved_stage)
        self._upsert_history(session, approved_stage, approved=True, completed=True)
        return self.store.save(session)

    def advance_stage(self, session_or_id: SessionState | str) -> SessionState:
        session = self._resolve_session(session_or_id)
        current = session.current_stage
        stage_def = self._stage_by_id[current]
        if stage_def.required_approval and current not in session.approved_stages:
            raise StageTransitionError(f"{current} must be approved before advancing")

        current_index = self._stage_order.index(current)
        if current_index == len(self._stage_order) - 1:
            return self.store.save(session)

        next_stage = self._stage_order[current_index + 1]
        session.current_stage = next_stage
        self._upsert_history(session, next_stage)
        return self.store.save(session)

    def rollback_to(
        self,
        session_or_id: SessionState | str,
        target_stage: str,
        reason: str = "",
    ) -> SessionState:
        session = self._resolve_session(session_or_id)
        if target_stage not in self._stage_order:
            raise StageTransitionError(f"unknown rollback target: {target_stage}")

        current_def = self._stage_by_id[session.current_stage]
        if target_stage not in current_def.rollback_targets:
            raise StageTransitionError(
                f"{session.current_stage} cannot roll back to {target_stage}; "
                f"allowed targets: {current_def.rollback_targets}"
            )

        session = self.rollback_manager.rollback(
            session=session,
            target_stage=target_stage,
            stage_order=self._stage_order,
            reason=reason,
        )
        self._upsert_history(session, target_stage, approved=False, completed=False)
        return self.store.save(session)

    def store_stage_response(
        self,
        session_or_id: SessionState | str,
        response: StageResponse,
    ) -> SessionState:
        session = self._resolve_session(session_or_id)
        if response.session_id != session.session_id:
            raise StageTransitionError("stage response session_id does not match session")
        if response.stage_id != session.current_stage:
            raise StageTransitionError(
                f"cannot store output for {response.stage_id}; "
                f"current stage is {session.current_stage}"
            )
        session.stage_outputs[response.stage_id] = response.output.model_dump(mode="json")
        self._upsert_history(
            session,
            response.stage_id,
            completed=True,
            status=response.status,
            prd_quality_status=response.output.prd_quality.status,
            prd_quality_score=response.output.prd_quality.score,
            required_user_input_count=len(response.output.required_user_input),
            risk_count=len(response.output.risks),
            rollback_targets=response.output.rollback_targets,
            summary=response.output.summary,
        )
        session.unresolved_questions = list(response.output.required_user_input)
        return self.store.save(session)

    def is_final_stage(self, stage_id: str) -> bool:
        return stage_id == self._stage_order[-1]

    def stage_ids(self) -> Iterable[str]:
        return tuple(self._stage_order)

    def _resolve_session(self, session_or_id: SessionState | str) -> SessionState:
        if isinstance(session_or_id, SessionState):
            return session_or_id
        return self.get_session(session_or_id)

    @staticmethod
    def _upsert_history(
        session: SessionState,
        stage_id: str,
        approved: Optional[bool] = None,
        completed: Optional[bool] = None,
        status: Optional[StageRunStatus] = None,
        prd_quality_status: Optional[str] = None,
        prd_quality_score: Optional[int] = None,
        required_user_input_count: Optional[int] = None,
        risk_count: Optional[int] = None,
        rollback_targets: Optional[list[str]] = None,
        summary: Optional[str] = None,
    ) -> None:
        for item in session.stage_history:
            if item.stage_id == stage_id:
                if approved is not None:
                    item.approved = approved
                if completed is not None:
                    item.completed = completed
                if status is not None:
                    item.status = status
                if prd_quality_status is not None:
                    item.prd_quality_status = prd_quality_status
                if prd_quality_score is not None:
                    item.prd_quality_score = prd_quality_score
                if required_user_input_count is not None:
                    item.required_user_input_count = required_user_input_count
                if risk_count is not None:
                    item.risk_count = risk_count
                if rollback_targets is not None:
                    item.rollback_targets = list(rollback_targets)
                if summary is not None:
                    item.summary = summary
                return

        session.stage_history.append(
            StageStatus(
                stage_id=stage_id,
                approved=bool(approved) if approved is not None else False,
                completed=bool(completed) if completed is not None else False,
                status=status,
                prd_quality_status=prd_quality_status,
                prd_quality_score=prd_quality_score,
                required_user_input_count=required_user_input_count or 0,
                risk_count=risk_count or 0,
                rollback_targets=list(rollback_targets or []),
                summary=summary,
            )
        )
