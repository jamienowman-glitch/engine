"""Vector search backend abstraction for Vector Explorer."""
from __future__ import annotations

from typing import Iterable, Protocol, Sequence

from engines.nexus.vector_explorer.schemas import VectorExplorerQuery


class VectorSearchBackend(Protocol):
    def query_by_id(self, anchor_id: str, query: VectorExplorerQuery) -> Iterable[tuple[str, float]]:
        ...

    def query_by_text(self, text: str, query: VectorExplorerQuery) -> Iterable[tuple[str, float]]:
        ...


class InMemoryVectorSearchBackend:
    """Fallback search backend using vectors stored on items (vector_ref as list)."""

    def __init__(self, vector_lookup: dict[str, Sequence[float]] | None = None) -> None:
        self._vectors = vector_lookup or {}

    def query_by_id(self, anchor_id: str, query: VectorExplorerQuery) -> Iterable[tuple[str, float]]:
        anchor_vec = self._vectors.get(anchor_id)
        if not anchor_vec:
            return []
        return self._nearest(anchor_vec, query.limit)

    def query_by_text(self, text: str, query: VectorExplorerQuery) -> Iterable[tuple[str, float]]:
        # No embeddings available in fallback path.
        return []

    def _nearest(self, anchor: Sequence[float], top_k: int) -> list[tuple[str, float]]:
        scored = []
        for item_id, vector in self._vectors.items():
            if not vector or len(vector) != len(anchor):
                continue
            score = _cosine_sim(anchor, vector)
            scored.append((item_id, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


def _cosine_sim(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
