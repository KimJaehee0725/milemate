"""GitHub retrieval provider boundary for future repository-backed evidence."""

from __future__ import annotations

from typing import Iterable, Optional

from app.backend.schemas.retrieval import RetrievalResult


class GitHubAdapter:
    def search(
        self,
        query: str,
        source_type: str = "technical_docs",
        scenario: Optional[str] = None,
        top_k: int = 5,
    ) -> Iterable[RetrievalResult | dict]:
        del query, source_type, scenario, top_k
        return []
