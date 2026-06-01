"""Session persistence backends for stage workflow state."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, Protocol

from app.backend.core.config_loader import RootConfig
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


class SQLiteSessionStore:
    """SQLite-backed session store for durable mock MVP state."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    @classmethod
    def from_config(cls, config: RootConfig) -> "SQLiteSessionStore":
        return cls(config.storage.stage_state_path)

    def get(self, session_id: str) -> SessionState:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            raise KeyError(session_id)
        return SessionState.model_validate(json.loads(row[0]))

    def save(self, session: SessionState) -> SessionState:
        payload = json.dumps(session.model_dump(mode="json"), ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, payload, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(session_id) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (session.session_id, payload),
            )
        return session.model_copy(deep=True)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
