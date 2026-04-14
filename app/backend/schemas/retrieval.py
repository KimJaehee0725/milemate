from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel

from .common import Citation


class RetrievalQuery(BaseModel):
    query: str
    source_type: str
    scenario: Optional[str] = None
    top_k: int = 5


class RetrievalResult(BaseModel):
    source_type: str
    title: str
    locator: str
    relevance_note: str
    snippet: Optional[str] = None

    def as_citation(self) -> Citation:
        return Citation(
            source_type=self.source_type,
            title=self.title,
            locator=self.locator,
            relevance_note=self.relevance_note,
        )
