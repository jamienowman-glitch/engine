"""Vector Store Repository."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Protocol

from engines.nexus.index.models import SearchResult


class VectorStore(Protocol):
    def upsert(self, id: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        ...

    def search(
        self, query_vector: List[float], filters: Optional[Dict[str, Any]], limit: int
    ) -> List[SearchResult]:
        ...


class InMemoryVectorStore:
    def __init__(self):
        # id -> (vector, metadata)
        self._store: Dict[str, dict] = {}

    def upsert(self, id: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        self._store[id] = {"vector": vector, "metadata": metadata}

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm_a = math.sqrt(sum(a * a for a in v1))
        norm_b = math.sqrt(sum(b * b for b in v2))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(
        self, query_vector: List[float], filters: Optional[Dict[str, Any]], limit: int
    ) -> List[SearchResult]:
        results = []
        for id, item in self._store.items():
            metadata = item["metadata"]
            
            # Apply filters
            if filters:
                match = True
                for k, v in filters.items():
                    # Exact match for now
                    if metadata.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            score = self._cosine_similarity(query_vector, item["vector"])
            results.append(SearchResult(id=id, score=score, metadata=metadata))

        # Sort desc by score
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
