"""MCP retrieval provider boundary.

The mock MVP keeps this provider no-network. A real MCP client can implement
the same search method and be injected into RetrievalAdapter.
"""

from __future__ import annotations

from typing import Iterable, Optional

from app.backend.schemas.retrieval import RetrievalResult


class MCPAdapter:
    def search(
        self,
        query: str,
        source_type: str = "technical_docs",
        scenario: Optional[str] = None,
        top_k: int = 5,
    ) -> Iterable[RetrievalResult | dict]:
        del query, source_type, scenario, top_k
        return []
