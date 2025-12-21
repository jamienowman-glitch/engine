"""Export Service (P5)."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict

from engines.scene_engine.core.scene_v2 import SceneV2
from engines.scene_engine.export.gltf_export import export_scene_to_gltf


class ExportFormat(str, Enum):
    GLTF_JSON = "gltf_json"
    GLTF_BINARY = "gltf_binary" # Not imp yet, defaulting to JSON with buffer uri
    # USDZ = "usdz" # Future


def export_scene(scene: SceneV2, fmt: ExportFormat = ExportFormat.GLTF_JSON) -> Dict[str, Any]:
    if fmt == ExportFormat.GLTF_JSON:
        return export_scene_to_gltf(scene)
    
    raise NotImplementedError(f"Format {fmt} not supported yet.")
