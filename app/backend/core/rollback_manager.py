"""Rollback mutation helper for stage workflow sessions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence
from uuid import uuid4

from app.backend.schemas.session import RollbackEvent, SessionState


class RollbackManager:
    """Apply rollback pruning and record auditable rollback events."""

    def rollback(
        self,
        session: SessionState,
        target_stage: str,
        stage_order: Sequence[str],
        reason: str = "",
    ) -> SessionState:
        from_stage = session.current_stage
        target_index = stage_order.index(target_stage)
        invalidated_stages = [
            stage_id
            for stage_id in stage_order[target_index:]
            if stage_id in session.stage_outputs or stage_id in session.approved_stages
        ]

        session.current_stage = target_stage
        session.approved_stages = [
            stage_id
            for stage_id in session.approved_stages
            if stage_order.index(stage_id) < target_index
        ]
        session.stage_outputs = {
            stage_id: output
            for stage_id, output in session.stage_outputs.items()
            if stage_order.index(stage_id) < target_index
        }
        session.unresolved_questions = []

        event = RollbackEvent(
            event_id=str(uuid4()),
            from_stage=from_stage,
            target_stage=target_stage,
            reason=reason,
            invalidated_stages=invalidated_stages,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        session.rollback_events.append(event)
        session.metadata["last_rollback_reason"] = reason
        session.metadata["last_rollback_event_id"] = event.event_id
        return session
