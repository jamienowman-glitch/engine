"""Asset library versioning and lineage tracking."""

from __future__ import annotations
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class VersionStatus(str, Enum):
    """Status of an asset version."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    DRAFT = "draft"


class AssetMetadata(BaseModel):
    """Metadata for an asset version."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    description: str = Field(default="")
    tags: List[str] = Field(default_factory=list)
    custom_meta: Dict[str, Any] = Field(default_factory=dict)


class AssetVersion(BaseModel):
    """A specific version of an asset."""
    asset_id: str = Field(..., description="Asset identifier")
    version_number: int = Field(..., ge=1, description="Version number (1, 2, 3, ...)")
    artifact_id: str = Field(..., description="Media artifact ID")
    status: VersionStatus = Field(default=VersionStatus.ACTIVE)
    metadata: AssetMetadata = Field(default_factory=AssetMetadata)
    previous_version: Optional[int] = Field(default=None, description="Previous version number")
    file_hash: str = Field(..., description="SHA256 hash of asset content")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    mime_type: str = Field(default="image/png")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class RenderLineageEntry(BaseModel):
    """Tracks which asset versions were used in a render."""
    asset_id: str = Field(..., description="Asset identifier")
    version_number: int = Field(..., description="Version used")
    layer_id: str = Field(..., description="Layer that used this asset")
    file_hash: str = Field(..., description="Hash for verification")


class RenderLineage(BaseModel):
    """Complete lineage of a render (which assets and versions were used)."""
    render_id: str = Field(..., description="Artifact ID of the render")
    composition_id: Optional[str] = Field(default=None)
    tenant_id: str
    env: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    assets_used: List[RenderLineageEntry] = Field(default_factory=list)
    composition_hash: str = Field(..., description="Hash of composition at render time")
    
    def get_asset_versions(self, asset_id: str) -> Optional[int]:
        """Get version used for a specific asset."""
        for entry in self.assets_used:
            if entry.asset_id == asset_id:
                return entry.version_number
        return None
    
    def get_all_assets(self) -> Dict[str, int]:
        """Get all assets and their versions used."""
        return {entry.asset_id: entry.version_number for entry in self.assets_used}
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class VersionComparison(BaseModel):
    """Comparison between two asset versions."""
    asset_id: str
    version_a: int
    version_b: int
    file_hash_a: str
    file_hash_b: str
    content_different: bool = Field(..., description="Whether file content differs")
    size_a: int
    size_b: int
    size_change_percent: float = Field(default=0.0)
    metadata_changes: Dict[str, Any] = Field(default_factory=dict)
    url_a: Optional[str] = None
    url_b: Optional[str] = None


class AssetVersioningService:
    """Service for managing asset versions and render lineage."""
    
    def __init__(self):
        """Initialize versioning service."""
        # In-memory storage (extensible to database)
        self._asset_versions: Dict[str, List[AssetVersion]] = {}
        self._render_lineage: Dict[str, RenderLineage] = {}
    
    def create_version(
        self,
        asset_id: str,
        artifact_id: str,
        file_hash: str,
        file_size: int,
        created_by: Optional[str] = None,
        description: str = "",
        tags: Optional[List[str]] = None,
        mime_type: str = "image/png",
    ) -> AssetVersion:
        """Create a new version of an asset."""
        if asset_id not in self._asset_versions:
            self._asset_versions[asset_id] = []
        
        versions = self._asset_versions[asset_id]
        version_number = len(versions) + 1
        previous = version_number - 1 if version_number > 1 else None
        
        version = AssetVersion(
            asset_id=asset_id,
            version_number=version_number,
            artifact_id=artifact_id,
            file_hash=file_hash,
            file_size=file_size,
            mime_type=mime_type,
            metadata=AssetMetadata(
                created_by=created_by,
                description=description,
                tags=tags or []
            ),
            previous_version=previous,
            status=VersionStatus.ACTIVE
        )
        
        versions.append(version)
        return version
    
    def get_version(self, asset_id: str, version_number: int) -> Optional[AssetVersion]:
        """Get a specific asset version."""
        if asset_id not in self._asset_versions:
            return None
        
        for version in self._asset_versions[asset_id]:
            if version.version_number == version_number:
                return version
        
        return None
    
    def get_latest_version(self, asset_id: str) -> Optional[AssetVersion]:
        """Get the latest active version of an asset."""
        if asset_id not in self._asset_versions:
            return None
        
        # Return latest active version
        for version in reversed(self._asset_versions[asset_id]):
            if version.status == VersionStatus.ACTIVE:
                return version
        
        return None
    
    def get_all_versions(self, asset_id: str) -> List[AssetVersion]:
        """Get all versions of an asset."""
        return self._asset_versions.get(asset_id, [])
    
    def deprecate_version(self, asset_id: str, version_number: int) -> bool:
        """Mark a version as deprecated."""
        version = self.get_version(asset_id, version_number)
        if not version:
            return False
        
        version.status = VersionStatus.DEPRECATED
        return True
    
    def archive_version(self, asset_id: str, version_number: int) -> bool:
        """Archive a version."""
        version = self.get_version(asset_id, version_number)
        if not version:
            return False
        
        version.status = VersionStatus.ARCHIVED
        return True
    
    def compare_versions(
        self,
        asset_id: str,
        version_a: int,
        version_b: int
    ) -> Optional[VersionComparison]:
        """Compare two versions of an asset."""
        v_a = self.get_version(asset_id, version_a)
        v_b = self.get_version(asset_id, version_b)
        
        if not v_a or not v_b:
            return None
        
        size_change_percent = 0.0
        if v_a.file_size > 0:
            size_change_percent = ((v_b.file_size - v_a.file_size) / v_a.file_size) * 100
        
        metadata_changes = {}
        if v_a.metadata.description != v_b.metadata.description:
            metadata_changes["description"] = {
                "from": v_a.metadata.description,
                "to": v_b.metadata.description
            }
        if v_a.metadata.tags != v_b.metadata.tags:
            metadata_changes["tags"] = {
                "added": [t for t in v_b.metadata.tags if t not in v_a.metadata.tags],
                "removed": [t for t in v_a.metadata.tags if t not in v_b.metadata.tags]
            }
        
        return VersionComparison(
            asset_id=asset_id,
            version_a=version_a,
            version_b=version_b,
            file_hash_a=v_a.file_hash,
            file_hash_b=v_b.file_hash,
            content_different=v_a.file_hash != v_b.file_hash,
            size_a=v_a.file_size,
            size_b=v_b.file_size,
            size_change_percent=size_change_percent,
            metadata_changes=metadata_changes
        )
    
    def record_render_lineage(
        self,
        render_id: str,
        tenant_id: str,
        env: str,
        assets_used: List[RenderLineageEntry],
        composition_id: Optional[str] = None,
        composition_hash: str = ""
    ) -> RenderLineage:
        """Record which asset versions were used in a render."""
        lineage = RenderLineage(
            render_id=render_id,
            composition_id=composition_id,
            tenant_id=tenant_id,
            env=env,
            assets_used=assets_used,
            composition_hash=composition_hash
        )
        
        self._render_lineage[render_id] = lineage
        return lineage
    
    def get_render_lineage(self, render_id: str) -> Optional[RenderLineage]:
        """Get lineage of a specific render."""
        return self._render_lineage.get(render_id)
    
    def get_renders_using_asset(self, asset_id: str, version_number: Optional[int] = None) -> List[RenderLineage]:
        """Find all renders that used a specific asset (and optionally version)."""
        renders = []
        
        for render_id, lineage in self._render_lineage.items():
            for entry in lineage.assets_used:
                if entry.asset_id == asset_id:
                    if version_number is None or entry.version_number == version_number:
                        renders.append(lineage)
                        break
        
        return renders
    
    def get_renders_for_composition(self, composition_id: str) -> List[RenderLineage]:
        """Get all renders for a composition."""
        return [
            lineage for render_id, lineage in self._render_lineage.items()
            if lineage.composition_id == composition_id
        ]
    
    def rerender_with_version(
        self,
        original_render_id: str,
        asset_id: str,
        new_version: int
    ) -> Optional[Dict[str, Any]]:
        """
        Prepare data for re-rendering with a different asset version.
        Returns the asset version info and original lineage.
        """
        lineage = self.get_render_lineage(original_render_id)
        if not lineage:
            return None
        
        new_asset_version = self.get_version(asset_id, new_version)
        if not new_asset_version:
            return None
        
        # Update lineage entry
        updated_lineage = {
            "original_render_id": original_render_id,
            "original_composition_id": lineage.composition_id,
            "original_assets": lineage.get_all_assets(),
            "asset_to_update": asset_id,
            "new_version": new_version,
            "new_artifact_id": new_asset_version.artifact_id,
            "old_artifact_id": next(
                (entry.asset_id for entry in lineage.assets_used if entry.asset_id == asset_id),
                None
            )
        }
        
        return updated_lineage
    
    def rollback_render(
        self,
        current_render_id: str,
        target_version_number: Optional[int] = None
    ) -> Optional[RenderLineage]:
        """
        Get the lineage to rollback to a previous version.
        If target_version_number not specified, goes to previous render.
        """
        lineage = self.get_render_lineage(current_render_id)
        if not lineage:
            return None
        
        # Find previous render for same composition
        composition_renders = self.get_renders_for_composition(lineage.composition_id)
        render_times = [(r.render_id, r.created_at) for r in composition_renders]
        render_times.sort(key=lambda x: x[1], reverse=True)
        
        # Find current render's position
        current_idx = next(
            (i for i, (rid, _) in enumerate(render_times) if rid == current_render_id),
            None
        )
        
        if current_idx is None or current_idx + 1 >= len(render_times):
            return None  # No previous render
        
        previous_render_id = render_times[current_idx + 1][0]
        return self.get_render_lineage(previous_render_id)


# Singleton instance
_default_versioning_service: Optional[AssetVersioningService] = None


def get_versioning_service() -> AssetVersioningService:
    """Get singleton versioning service."""
    global _default_versioning_service
    if _default_versioning_service is None:
        _default_versioning_service = AssetVersioningService()
    return _default_versioning_service
