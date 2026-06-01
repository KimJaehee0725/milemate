"""Retrieval coordinator and deterministic no-network providers."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Protocol

from app.backend.core.config_loader import RootConfig, load_app_config
from app.backend.schemas.retrieval import RetrievalResult


class RetrievalProvider(Protocol):
    """Provider boundary for MCP, GitHub, web, legal, or local retrieval."""

    def search(
        self,
        query: str,
        source_type: str = "technical_docs",
        scenario: Optional[str] = None,
        top_k: int = 5,
    ) -> Iterable[RetrievalResult | dict]:
        """Return retrieval results without mutating coordinator state."""


class StaticRetrievalProvider:
    """Return citation-shaped results without network access."""

    _SOURCE_TITLES: Dict[str, str] = {
        "papers": "Last-mile delivery planning research note",
        "technical_docs": "Route optimization and dispatch system design note",
        "laws": "Korean privacy and location data compliance note",
        "patents": "Dispatch recommendation patent landscape memo",
        "datasets": "Synthetic last-mile operations dataset schema",
        "industry_cases": "Dynamic dispatch industry case summary",
    }

    def search(
        self,
        query: str,
        source_type: str = "technical_docs",
        scenario: Optional[str] = None,
        top_k: int = 5,
    ) -> List[RetrievalResult]:
        result = RetrievalResult(
            source_type=source_type,
            title=self._SOURCE_TITLES.get(source_type, f"{source_type} mock reference"),
            locator=f"mock://{source_type}/{scenario or 'general'}",
            relevance_note=(
                f"Mock evidence for '{query}' aligned to the {source_type} source category."
            ),
            snippet=(
                "Deterministic MVP evidence: use order state, courier location, and zone "
                "metadata before expanding optimization scope."
            ),
            metadata={"provider": "static", "scenario": scenario or "general"},
        )
        return [result for _ in range(max(1, min(top_k, 1)))]


class RetrievalAdapter:
    """Coordinate retrieval providers and normalize citation-ready results."""

    def __init__(
        self,
        providers: Optional[List[RetrievalProvider]] = None,
        config: Optional[RootConfig] = None,
    ) -> None:
        self.config = config or load_app_config()
        self.providers = providers or [StaticRetrievalProvider()]

    def search(
        self,
        query: str,
        source_type: str = "technical_docs",
        scenario: Optional[str] = None,
        top_k: int = 5,
    ) -> List[dict]:
        if source_type not in self.config.sources.categories:
            raise ValueError(f"unknown source_type: {source_type}")

        results: List[RetrievalResult] = []
        for provider in self.providers:
            for item in provider.search(
                query=query,
                source_type=source_type,
                scenario=scenario,
                top_k=top_k,
            ):
                result = (
                    item
                    if isinstance(item, RetrievalResult)
                    else RetrievalResult.model_validate(item)
                )
                results.append(result)
                if len(results) >= top_k:
                    break
            if len(results) >= top_k:
                break

        return [result.model_dump(mode="json") for result in results[:top_k]]
