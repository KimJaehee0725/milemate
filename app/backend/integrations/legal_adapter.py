"""Mock Korean law adapter backed by the configured legalize-kr source."""

from __future__ import annotations

from typing import List

from app.backend.schemas.retrieval import RetrievalResult


class LegalAdapter:
    """Return local, citation-ready Korean law search results."""

    def search(self, query: str) -> List[dict]:
        result = RetrievalResult(
            source_type="laws",
            title="legalize-kr location and personal information review note",
            locator="knowledge/laws/legalize-kr-notes.md",
            relevance_note=(
                f"Mock legal check for '{query}' covering location data minimization, "
                "notice, and retention constraints."
            ),
            snippet=(
                "Use only dispatch-critical location data and expose retention rules in the MVP."
            ),
            metadata={
                "provider": "legalize-kr-local-note",
                "disclaimer": "Reference material only; not legal advice.",
            },
        )
        return [result.model_dump(mode="json")]
