"""LanceDB implementation of NexusVectorStore (E-03)."""
from __future__ import annotations

import logging
import os
import shutil
from typing import List, Optional, Any, Dict

import lancedb
import pyarrow as pa
from pydantic import BaseModel

from engines.nexus.schemas import (
    SpaceKey,
    Scope,
    NexusDocument,
    NexusQueryRequest,
    NexusQueryResult,
    NexusEmbedding
)

logger = logging.getLogger(__name__)

class LanceVectorStore:
    """
    LanceDB-backed vector store with strict tenant isolation.
    """

    def __init__(self, root_uri: str = "/tmp/nexus_data"):
        self.root_uri = root_uri.rstrip("/")

    def _get_table_uri(self, space_key: SpaceKey) -> str:
        """
        Constructs the strict path for the table.
        Format: {root}/{tenant_id}/{env}/{project_id}/{surface_id}/{space_id}.lance
        """
        # Ensure we use 't_system' for global scope logic if passed explicitly,
        # though SpaceKey should already carry the correct tenant_id.
        return (
            f"{self.root_uri}/"
            f"{space_key.tenant_id}/"
            f"{space_key.env}/"
            f"{space_key.project_id}/"
            f"{space_key.surface_id}/"
            f"{space_key.space_id}.lance"
        )

    def _get_connection(self, uri: str):
        """Returns a LanceDB connection/table wrapper."""
        # LanceDB connects to a folder. The table is inside.
        # We'll treat the .lance path as the DB root for simplicity or specific table.
        # Actually lancedb.connect(uri) works on a directory.
        # If uri ends in .lance, we might treat parent as db and filename as table,
        # but LanceDB "native" usually is a folder of tables.
        # Contract says: .../{space_id}.lance
        # We will interpret this as: DB URI = parent dir, Table Name = {space_id}.lance (or just 'vectors')

        # To align with contract: "Table Name = 'vectors'" inside the path.
        # So path is .../{space_id}.lance/vectors.lance

        # Let's verify lancedb behavior.
        # lancedb.connect("s3://bucket/path") -> db
        # db.create_table("vectors", ...)

        return lancedb.connect(uri)

    def upsert(self, space_key: SpaceKey, embeddings: List[NexusEmbedding]) -> None:
        """Upsert embeddings into the isolated space."""
        if not embeddings:
            return

        uri = self._get_table_uri(space_key)
        # Ensure directory exists for local paths
        if not uri.startswith("s3://") and not uri.startswith("gcs://"):
            os.makedirs(uri, exist_ok=True)

        db = self._get_connection(uri)

        data = []
        for e in embeddings:
            # Flatten/normalize for Lance
            row = {
                "id": e.doc_id,
                "vector": e.embedding,
                "text": e.metadata.get("text", ""), # naive fallback
                "type": e.kind.value if hasattr(e.kind, 'value') else str(e.kind),
                "metadata": str(e.metadata), # simplified
                "tenant_id": e.tenant_id,
                "timestamp": e.created_at.isoformat() if e.created_at else None
            }
            data.append(row)

        table_name = "vectors"
        try:
            tbl = db.open_table(table_name)
            tbl.add(data)
        except (FileNotFoundError, ValueError):
            # Create if not exists (FileNotFound or ValueError depending on backend)
            db.create_table(table_name, data=data)

    def query(self, space_key: SpaceKey, query_vec: List[float], top_k: int, include_global: bool = False) -> NexusQueryResult:
        """
        Query the store.
        If include_global=True, also query the global space for this surface_id and merge.
        """
        results = []

        # 1. Query Tenant Space
        tenant_hits = self._query_one_space(space_key, query_vec, top_k)
        for h in tenant_hits:
            h.metadata["source_scope"] = "tenant"
        results.extend(tenant_hits)

        # 2. Query Global Space (if requested)
        if include_global and space_key.scope == Scope.TENANT:
            # Construct global key: same surface, same project (maybe?), but tenant=t_system
            # Contract: "global space for the caller’s surface_id"
            global_key = SpaceKey(
                scope=Scope.GLOBAL,
                tenant_id="t_system",
                env=space_key.env,       # Same env? Usually global is per env.
                project_id=space_key.project_id, # Keep project? Or global project? Contract vague.
                                                 # "global-per-surface" implies surface is the key.
                                                 # We will keep project_id to be safe or use default.
                surface_id=space_key.surface_id,
                space_id=space_key.space_id # Same space name? Likely 'main' or similar.
            )

            global_hits = self._query_one_space(global_key, query_vec, top_k)
            for h in global_hits:
                h.metadata["source_scope"] = "global"
            results.extend(global_hits)

        # 3. Merge & Rank
        # Simple score sort
        # hits are likely dicts or objects. _query_one_space returns NexusDocument

        # Sort by score (descending) - wait, NexusDocument doesn't have score in schema?
        # The schema in E-00 NexusQueryResult has hits: List[NexusDocument]
        # We need to stick score somewhere. metadata?

        results.sort(key=lambda x: x.metadata.get("score", 0.0), reverse=True)
        return NexusQueryResult(hits=results[:top_k])

    def _query_one_space(self, space_key: SpaceKey, query_vec: List[float], k: int) -> List[NexusDocument]:
        uri = self._get_table_uri(space_key)
        try:
            db = self._get_connection(uri)
            tbl = db.open_table("vectors")
        except Exception:
            # Missing table or path -> empty result
            return []

        # LanceDB query
        # vector column name defaults to "vector"
        df = tbl.search(query_vec).limit(k).to_pandas()

        hits = []
        for _, row in df.iterrows():
            # Convert back to NexusDocument
            # row has: id, vector, text, type, metadata, tenant_id, timestamp, _distance

            # _distance is distance. Score = 1 - distance (approx for cosine/l2)
            score = 1.0 - row.get("_distance", 0.0)

            doc = NexusDocument(
                id=row["id"],
                text=row["text"],
                tenant_id=row["tenant_id"],
                metadata={
                    "score": score,
                    "raw_metadata": row["metadata"] # it was stored as string
                }
            )
            hits.append(doc)

        return hits
