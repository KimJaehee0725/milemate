"""In-memory session store for the demo workflow."""

from __future__ import annotations

from typing import Dict, Protocol

from app.backend.schemas.session import SessionState


class SessionStore(Protocol):
    """Persistence boundary used by StageManager."""

    def get(self, session_id: str) -> SessionState:
        """Return a session or raise KeyError."""

    def save(self, session: SessionState) -> SessionState:
        """Persist and return the saved session."""


class InMemorySessionStore:
    """Process-local session store used by tests and lightweight demos."""

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState:
        try:
            return self._sessions[session_id].model_copy(deep=True)
        except KeyError as exc:
            raise KeyError(session_id) from exc

    def save(self, session: SessionState) -> SessionState:
        self._sessions[session.session_id] = session.model_copy(deep=True)
        return session.model_copy(deep=True)
