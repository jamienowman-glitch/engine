"""CAD Import/Export Bridge (STEP/IGES)."""
from __future__ import annotations

from engines.scene_engine.core.scene_v2 import SceneV2

def import_step(file_path: str) -> SceneV2:
    """
    Imports a STEP file into SceneV2.
    
    P0 Stub: Raises NotImplementedError.
    Future: Use `pythonocc-core` or `ezdxf` equivalent?
    """
    raise NotImplementedError("STEP Import not yet implemented in Phase 8.")

def export_step(scene: SceneV2, file_path: str):
    """
    Exports SceneV2 to STEP.
    """
    raise NotImplementedError("STEP Export not yet implemented in Phase 8.")
