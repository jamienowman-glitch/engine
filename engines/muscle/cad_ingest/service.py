"""
CAD Ingest Service - Orchestrate parsing, normalization, healing, and artifact registration.

Implements:
- Adapter selection based on format
- Units normalization and validation
- Topology healing orchestration
- Caching by source_sha256 + params
- Media v2 artifact registration
"""

from __future__ import annotations

import hashlib
import time
from typing import Dict, Optional, Tuple

from engines.cad_ingest.models import (
    CadIngestRequest,
    CadIngestResponse,
    CadModel,
    UnitKind,
)
from engines.cad_ingest.dxf_adapter import dxf_to_cad_model
from engines.cad_ingest.ifc_lite_adapter import ifc_lite_to_cad_model
from engines.cad_ingest.topology_heal import heal_topology
from engines.media_v2.service import get_media_service
from engines.media_v2.models import ArtifactCreateRequest


class CadIngestCache:
    """Simple in-memory cache for CAD models."""
    
    def __init__(self, max_entries: int = 100):
        self.cache: Dict[str, CadModel] = {}
        self.max_entries = max_entries
    
    def cache_key(self, source_sha256: str, params_hash: str) -> str:
        """Generate cache key from source + params."""
        return f"{source_sha256}:{params_hash}"
    
    def get(self, key: str) -> Optional[CadModel]:
        """Retrieve cached model."""
        return self.cache.get(key)
    
    def put(self, key: str, model: CadModel) -> None:
        """Store model in cache (with simple eviction)."""
        if len(self.cache) >= self.max_entries:
            # Simple FIFO eviction
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        self.cache[key] = model
    
    def clear(self) -> None:
        """Clear cache."""
        self.cache.clear()


class CadIngestService:
    """Orchestrate CAD ingest pipeline."""
    
    def __init__(self):
        self.cache = CadIngestCache()
    
    def _detect_format(
        self, content: bytes, format_hint: Optional[str] = None
    ) -> str:
        """Detect file format from content or hint."""
        if format_hint:
            fmt = format_hint.lower()
            if fmt in ("dxf", "ifc-lite", "ifc"):
                return fmt if fmt != "ifc" else "ifc-lite"
        
        # Auto-detect from content
        text = content[:1000].decode("utf-8", errors="ignore").lower()
        
        if "section" in text and "entities" in text:
            return "dxf"
        elif "ifc" in text or "{" in text:
            # Might be JSON IFC-lite
            return "ifc-lite"
        else:
            return "unknown"
    
    def _params_hash(self, request: CadIngestRequest) -> str:
        """Hash request parameters for cache key."""
        key = f"{request.tolerance}:{request.snap_to_grid}:{request.grid_size}:{request.unit_hint}"
        return hashlib.sha256(key.encode()).hexdigest()[:8]
    
    def _validate_request(self, request: CadIngestRequest) -> None:
        """Validate ingest request parameters."""
        if request.max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb must be positive")
        if request.max_timeout_s <= 0:
            raise ValueError("max_timeout_s must be positive")
        if request.tolerance <= 0:
            raise ValueError("tolerance must be positive")
    
    def ingest(
        self, content: bytes, request: CadIngestRequest
    ) -> Tuple[CadModel, CadIngestResponse]:
        """
        Ingest CAD file content and return normalized model + response.
        
        Args:
            content: File bytes
            request: Ingest parameters
        
        Returns:
            (CadModel, CadIngestResponse)
        
        Raises:
            ValueError: For invalid parameters, format, or units
            RuntimeError: For parsing or healing failures
        """
        # Validate
        self._validate_request(request)
        
        # Check size
        size_mb = len(content) / (1024 * 1024)
        if size_mb > request.max_file_size_mb:
            raise ValueError(
                f"File size {size_mb:.1f} MB exceeds limit {request.max_file_size_mb} MB"
            )
        
        # Check cache
        source_sha256 = hashlib.sha256(content).hexdigest()
        params_hash = self._params_hash(request)
        cache_key = self.cache.cache_key(source_sha256, params_hash)
        
        cached_model = self.cache.get(cache_key)
        if cached_model:
            response = self._model_to_response(cached_model, request)
            return cached_model, response
        
        # Detect format
        detected_fmt = self._detect_format(content, request.format_hint)
        if detected_fmt == "unknown":
            raise ValueError("Could not detect file format; provide format_hint (dxf|ifc-lite)")
        
        # Parse and normalize
        start_time = time.time()
        
        try:
            if detected_fmt == "dxf":
                model = dxf_to_cad_model(
                    content,
                    unit_hint=request.unit_hint,
                    tolerance=request.tolerance,
                )
            elif detected_fmt == "ifc-lite":
                model = ifc_lite_to_cad_model(
                    content,
                    unit_hint=request.unit_hint,
                    tolerance=request.tolerance,
                )
            else:
                raise ValueError(f"Unsupported format: {detected_fmt}")
        except Exception as exc:
            raise RuntimeError(f"Failed to parse {detected_fmt} file: {exc}") from exc
        
        # Apply topology healing
        healed_entities, healing_actions = heal_topology(
            model.entities,
            tolerance=request.tolerance,
            snap_to_grid=request.snap_to_grid,
            grid_size=request.grid_size,
        )
        model.entities = healed_entities
        model.healing_actions = healing_actions
        
        elapsed_s = time.time() - start_time
        if elapsed_s > request.max_timeout_s:
            raise RuntimeError(
                f"Ingest timed out ({elapsed_s:.1f}s > {request.max_timeout_s}s)"
            )
        
        # Cache result
        self.cache.put(cache_key, model)
        
        # Build response
        response = self._model_to_response(model, request)
        
        return model, response
    
    def _model_to_response(
        self, model: CadModel, request: CadIngestRequest
    ) -> CadIngestResponse:
        """Convert CadModel to response object."""
        # Would be populated by caller after artifact registration
        return CadIngestResponse(
            cad_model_artifact_id="",  # Set by caller
            model_id=model.id,
            units=model.units,
            entity_count=len(model.entities),
            layer_count=len(model.layers),
            healing_actions_count=len(model.healing_actions),
            bbox=model.bbox,
            model_hash=model.model_hash or "",
            source_sha256=model.source_sha256,
            created_at=model.created_at,
            meta=model.meta,
        )
    
    def register_artifact(
        self, model: CadModel, request: CadIngestRequest
    ) -> str:
        """
        Register CAD model as media_v2 artifact.
        Returns artifact ID.
        """
        media_service = get_media_service()
        
        # First, create parent asset
        from engines.media_v2.models import MediaUploadRequest, MediaAsset
        
        upload_req = MediaUploadRequest(
            tenant_id=request.tenant_id,
            env=request.env,
            user_id=request.user_id,
            kind="other",
            source_uri=request.source_uri or request.file_uri or "cad_model",
            source_ref=model.source_sha256,
            tags=["cad", "ingest"],
            meta={
                "format": model.source_format,
                "units": model.units.value,
                "tolerance_used": model.tolerance,
                "healing_actions_summary": len(model.healing_actions),
                "adapter_version": model.adapter_version,
            },
        )
        
        # Register as a "synthetic" asset without actual file bytes
        asset = media_service.register_remote(upload_req)
        
        # Create derived artifact for the CadModel
        artifact_req = ArtifactCreateRequest(
            tenant_id=request.tenant_id,
            env=request.env,
            parent_asset_id=asset.id,
            kind="cad_model",  # type: ignore
            uri=f"cad://{model.id}",
            meta={
                "model_id": model.id,
                "entity_count": len(model.entities),
                "layer_count": len(model.layers),
                "bbox_min": model.bbox.min.model_dump(),
                "bbox_max": model.bbox.max.model_dump(),
                "model_hash": model.model_hash,
                "source_sha256": model.source_sha256,
                "healing_actions_count": len(model.healing_actions),
            },
        )
        
        artifact = media_service.register_artifact(artifact_req)
        return artifact.id


# Module-level default service
_default_service: Optional[CadIngestService] = None


def get_cad_ingest_service() -> CadIngestService:
    """Get default CAD ingest service."""
    global _default_service
    if _default_service is None:
        _default_service = CadIngestService()
    return _default_service


def set_cad_ingest_service(service: CadIngestService) -> None:
    """Override default service (for testing)."""
    global _default_service
    _default_service = service
