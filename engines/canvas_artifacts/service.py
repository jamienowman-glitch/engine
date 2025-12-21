from __future__ import annotations

import uuid
from typing import Optional
from engines.canvas_artifacts.models import ArtifactRef
from engines.canvas_artifacts.storage import artifact_storage, ArtifactStorage

async def upload_artifact(
    canvas_id: str,
    data: bytes,
    mime_type: str,
    user_id: str,
    tenant_id: str,
    env: str,
    storage: ArtifactStorage = artifact_storage
) -> ArtifactRef:
    artifact_id = uuid.uuid4().hex
    key = f"tenants/{tenant_id}/{env}/canvas/{canvas_id}/{artifact_id}"
    
    url = await storage.upload(key, data, mime_type)
    
    return ArtifactRef(
        id=artifact_id,
        canvas_id=canvas_id,
        size=len(data),
        mime_type=mime_type,
        url=url,
        created_by=user_id,
        key=key
    )

async def get_artifact(artifact_id: str) -> None:
    # Logic to fetch metadata if we had a repo.
    # For now metadata is returned on upload.
    # Future: engines/canvas_artifacts/repository.py
    pass
