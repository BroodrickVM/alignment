"""Future research retrieval boundary; no fabricated research or citations.

Retrieval-augmented generation (RAG) is not implemented. The current agent
does not invoke this component. Verified evidence must be curated first.
"""
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ResearchEvidence:
    """Future evidence record with traceable source and reviewed relevance."""

    source_id: str
    citation: str
    excerpt: str


class ResearchRetriever:
    """Explicitly unimplemented interface to prevent implied research grounding."""

    def retrieve(self, query: str) -> Tuple[ResearchEvidence, ...]:
        """Fail visibly until an evidence-backed retrieval implementation exists."""
        raise NotImplementedError('Research retrieval is pending; no evidence sources have been loaded.')
