"""Service for Scene Store (Level B)."""
from __future__ import annotations

from typing import Any, Optional

try:
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None

from engines.config import runtime_config
from engines.scene_engine.core.scene_v2 import SceneV2
from engines.scene_engine.store.models import (
    LoadSceneRequest,
    LoadSceneResult,
    SaveSceneRequest,
    SaveSceneResult,
)


class SceneStoreService:
    def __init__(self, client: Any = None) -> None:
        if firestore is None:
            # warn or raise if strictly required, but allow mock/in-memory fallback for tests if needed?
            # For now, follow repo pattern:
            pass 
        self._client = client or self._default_client()
        cfg = runtime_config.config_snapshot()
        self._tenant = cfg.get("tenant_id") or ""

    def _default_client(self):
        if firestore is None:
            return None
        project = runtime_config.get_firestore_project()
        if not project:
            return None # Should handle gracefully or raise
        return firestore.Client(project=project)

    def _collection(self, tenant_id: str):
        if not self._client:
            raise RuntimeError("Firestore client not initialized")
        suffix = tenant_id or self._tenant or "t_unknown"
        return self._client.collection(f"scene_v2_store_{suffix}")

    def save_scene(self, request: SaveSceneRequest) -> SaveSceneResult:
        # Pydantic dump for serialization
        data = request.scene.model_dump()
        
        # Add metadata envelope
        envelope = {
            "scene_id": request.scene.id,
            "scene_data": data,
            "name": request.name,
            "tags": request.tags or [],
            "meta": request.meta,
        }
        
        col = self._collection(self._tenant)
        col.document(request.scene.id).set(envelope)
        
        return SaveSceneResult(scene_id=request.scene.id)

    def load_scene(self, request: LoadSceneRequest) -> LoadSceneResult:
        col = self._collection(self._tenant)
        doc = col.document(request.scene_id).get()
        
        if not doc.exists:
            raise ValueError(f"Scene {request.scene_id} not found")
            
        data = doc.to_dict() or {}
        scene_data = data.get("scene_data")
        if not scene_data:
            raise ValueError("Corrupt scene data")
            
        # Rehydrate SceneV2
        scene = SceneV2.model_validate(scene_data)
        
        return LoadSceneResult(scene=scene)
