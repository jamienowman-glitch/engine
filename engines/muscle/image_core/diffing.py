"""Composition diffing and comparison system."""

from __future__ import annotations
from typing import Optional, Dict, List, Any, Tuple
from pydantic import BaseModel, Field
from enum import Enum


class DiffType(str, Enum):
    """Type of difference detected."""
    LAYER_ADDED = "layer_added"
    LAYER_REMOVED = "layer_removed"
    LAYER_MODIFIED = "layer_modified"
    PROPERTY_CHANGED = "property_changed"
    EFFECT_ADDED = "effect_added"
    EFFECT_REMOVED = "effect_removed"


class LayerDiff(BaseModel):
    """Difference in a single layer."""
    layer_id: str
    layer_name: str
    diff_type: DiffType
    property_name: Optional[str] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    description: str = ""


class CompositionDiff(BaseModel):
    """Complete diff between two compositions."""
    composition_a_id: Optional[str] = None
    composition_b_id: Optional[str] = None
    render_a_id: Optional[str] = None
    render_b_id: Optional[str] = None
    
    width_a: int
    height_a: int
    width_b: int
    height_b: int
    
    background_color_a: str
    background_color_b: str
    
    layer_diffs: List[LayerDiff] = Field(default_factory=list)
    properties_changed: Dict[str, Tuple[Any, Any]] = Field(default_factory=dict)
    
    total_changes: int = 0
    similarity_score: float = Field(default=1.0, ge=0.0, le=1.0)
    
    def add_layer_diff(self, diff: LayerDiff) -> None:
        """Add a layer difference."""
        self.layer_diffs.append(diff)
        self.total_changes += 1
    
    def add_property_change(self, prop_name: str, old_val: Any, new_val: Any) -> None:
        """Record a property change."""
        self.properties_changed[prop_name] = (old_val, new_val)
        self.total_changes += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of changes."""
        return {
            "total_changes": self.total_changes,
            "layers_added": len([d for d in self.layer_diffs if d.diff_type == DiffType.LAYER_ADDED]),
            "layers_removed": len([d for d in self.layer_diffs if d.diff_type == DiffType.LAYER_REMOVED]),
            "layers_modified": len([d for d in self.layer_diffs if d.diff_type == DiffType.LAYER_MODIFIED]),
            "properties_changed": len(self.properties_changed),
            "similarity_score": self.similarity_score,
        }


class DiffReport(BaseModel):
    """Detailed diff report for presentation/logging."""
    title: str
    comparison_a: str
    comparison_b: str
    timestamp: str
    diff: CompositionDiff
    
    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            f"# {self.title}",
            f"**Comparison A:** {self.comparison_a}",
            f"**Comparison B:** {self.comparison_b}",
            f"**Timestamp:** {self.timestamp}",
            "",
            "## Summary",
            f"- Total Changes: {self.diff.total_changes}",
            f"- Similarity Score: {self.diff.similarity_score * 100:.1f}%",
            f"- Layers Added: {self.diff.get_summary()['layers_added']}",
            f"- Layers Removed: {self.diff.get_summary()['layers_removed']}",
            f"- Layers Modified: {self.diff.get_summary()['layers_modified']}",
            f"- Properties Changed: {self.diff.get_summary()['properties_changed']}",
            "",
        ]
        
        if self.diff.width_a != self.diff.width_b or self.diff.height_a != self.diff.height_b:
            lines.extend([
                "## Dimension Changes",
                f"- Width: {self.diff.width_a} → {self.diff.width_b}",
                f"- Height: {self.diff.height_a} → {self.diff.height_b}",
                "",
            ])
        
        if self.diff.background_color_a != self.diff.background_color_b:
            lines.extend([
                "## Background Color Change",
                f"- Old: {self.diff.background_color_a}",
                f"- New: {self.diff.background_color_b}",
                "",
            ])
        
        if self.diff.layer_diffs:
            lines.extend([
                "## Layer Changes",
                "",
            ])
            for layer_diff in self.diff.layer_diffs:
                lines.append(f"### Layer: {layer_diff.layer_name} (`{layer_diff.layer_id}`)")
                lines.append(f"**Type:** {layer_diff.diff_type}")
                if layer_diff.property_name:
                    lines.append(f"**Property:** {layer_diff.property_name}")
                    lines.append(f"**Old Value:** {layer_diff.old_value}")
                    lines.append(f"**New Value:** {layer_diff.new_value}")
                if layer_diff.description:
                    lines.append(f"**Description:** {layer_diff.description}")
                lines.append("")
        
        if self.diff.properties_changed:
            lines.extend([
                "## Composition Property Changes",
                "",
            ])
            for prop, (old_val, new_val) in self.diff.properties_changed.items():
                lines.append(f"- **{prop}:** `{old_val}` → `{new_val}`")
            lines.append("")
        
        return "\n".join(lines)
    
    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "title": self.title,
            "comparison_a": self.comparison_a,
            "comparison_b": self.comparison_b,
            "timestamp": self.timestamp,
            "diff": self.diff.dict(),
        }


class CompositionDiffer:
    """Engine for comparing compositions and renders."""
    
    @staticmethod
    def compare_compositions(comp_a, comp_b, id_a: str = "", id_b: str = "") -> CompositionDiff:
        """
        Compare two ImageComposition objects.
        
        Args:
            comp_a: First composition
            comp_b: Second composition
            id_a: Optional ID/name of composition A
            id_b: Optional ID/name of composition B
        
        Returns:
            CompositionDiff with all detected differences
        """
        diff = CompositionDiff(
            composition_a_id=id_a,
            composition_b_id=id_b,
            width_a=comp_a.width,
            height_a=comp_a.height,
            width_b=comp_b.width,
            height_b=comp_b.height,
            background_color_a=comp_a.background_color,
            background_color_b=comp_b.background_color,
        )
        
        # Compare dimensions
        if comp_a.width != comp_b.width or comp_a.height != comp_b.height:
            diff.add_property_change(
                "dimensions",
                f"{comp_a.width}x{comp_a.height}",
                f"{comp_b.width}x{comp_b.height}"
            )
        
        # Compare background color
        if comp_a.background_color != comp_b.background_color:
            diff.add_property_change(
                "background_color",
                comp_a.background_color,
                comp_b.background_color
            )
        
        # Compare layers
        layers_a = {layer.id: layer for layer in comp_a.layers}
        layers_b = {layer.id: layer for layer in comp_b.layers}
        
        # Detect removed layers
        for layer_id in layers_a.keys():
            if layer_id not in layers_b:
                layer = layers_a[layer_id]
                diff.add_layer_diff(LayerDiff(
                    layer_id=layer_id,
                    layer_name=layer.name,
                    diff_type=DiffType.LAYER_REMOVED,
                    description=f"Layer '{layer.name}' was removed"
                ))
        
        # Detect added/modified layers
        for layer_id in layers_b.keys():
            if layer_id not in layers_a:
                layer = layers_b[layer_id]
                diff.add_layer_diff(LayerDiff(
                    layer_id=layer_id,
                    layer_name=layer.name,
                    diff_type=DiffType.LAYER_ADDED,
                    description=f"Layer '{layer.name}' was added"
                ))
            else:
                # Compare layer properties
                layer_a = layers_a[layer_id]
                layer_b = layers_b[layer_id]
                
                layer_diff = CompositionDiffer._compare_layers(layer_a, layer_b)
                if layer_diff:
                    diff.add_layer_diff(layer_diff)
        
        # Calculate similarity
        diff.similarity_score = CompositionDiffer._calculate_similarity(diff)
        
        return diff
    
    @staticmethod
    def _compare_layers(layer_a, layer_b) -> Optional[LayerDiff]:
        """Compare two layers for changes."""
        changes = []
        
        # Check basic properties
        if layer_a.x != layer_b.x:
            changes.append(f"x: {layer_a.x} → {layer_b.x}")
        if layer_a.y != layer_b.y:
            changes.append(f"y: {layer_a.y} → {layer_b.y}")
        if layer_a.width != layer_b.width:
            changes.append(f"width: {layer_a.width} → {layer_b.width}")
        if layer_a.height != layer_b.height:
            changes.append(f"height: {layer_a.height} → {layer_b.height}")
        if layer_a.opacity != layer_b.opacity:
            changes.append(f"opacity: {layer_a.opacity} → {layer_b.opacity}")
        if layer_a.color != layer_b.color:
            changes.append(f"color: {layer_a.color} → {layer_b.color}")
        if layer_a.asset_id != layer_b.asset_id:
            changes.append(f"asset_id: {layer_a.asset_id} → {layer_b.asset_id}")
        if layer_a.text != layer_b.text:
            changes.append(f"text changed")
        if layer_a.blend_mode != layer_b.blend_mode:
            changes.append(f"blend_mode: {layer_a.blend_mode} → {layer_b.blend_mode}")
        
        if changes:
            return LayerDiff(
                layer_id=layer_a.id,
                layer_name=layer_a.name,
                diff_type=DiffType.LAYER_MODIFIED,
                description="Layer properties modified: " + ", ".join(changes[:3])
            )
        
        return None
    
    @staticmethod
    def _calculate_similarity(diff: CompositionDiff) -> float:
        """Calculate similarity score based on differences."""
        # More changes = lower similarity
        # Start at 1.0 (identical)
        max_changes = 20  # Max before 0 similarity
        
        if diff.total_changes == 0:
            return 1.0
        
        score = 1.0 - (diff.total_changes / max_changes)
        return max(0.0, score)
    
    @staticmethod
    def compare_pixel_hashes(hash_a: str, hash_b: str) -> Dict[str, Any]:
        """
        Compare two render hashes for content differences.
        (Simplified: just checks equality)
        
        Args:
            hash_a: Hash of first render
            hash_b: Hash of second render
        
        Returns:
            Comparison result
        """
        return {
            "hashes_match": hash_a == hash_b,
            "hash_a": hash_a,
            "hash_b": hash_b,
            "content_identical": hash_a == hash_b,
            "similarity": 1.0 if hash_a == hash_b else 0.0,
        }
    
    @staticmethod
    def compare_artifact_dimensions(
        width_a: int,
        height_a: int,
        width_b: int,
        height_b: int,
    ) -> Dict[str, Any]:
        """Compare dimensions of two renders."""
        width_diff = width_b - width_a
        height_diff = height_b - height_a
        
        width_pct = (width_diff / width_a * 100) if width_a > 0 else 0
        height_pct = (height_diff / height_a * 100) if height_a > 0 else 0
        
        return {
            "width_a": width_a,
            "height_a": height_a,
            "width_b": width_b,
            "height_b": height_b,
            "width_change": width_diff,
            "height_change": height_diff,
            "width_change_pct": width_pct,
            "height_change_pct": height_pct,
            "dimensions_match": width_a == width_b and height_a == height_b,
        }


def get_differ() -> CompositionDiffer:
    """Get composition differ instance."""
    return CompositionDiffer()
