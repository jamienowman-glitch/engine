"""Material Engine Schemas (The Paint)."""
from __future__ import annotations
from enum import Enum
from typing import List, Dict, Optional, Union
from pydantic import BaseModel, Field

class MaterialType(str, Enum):
    PBR = "PBR"
    UNLIT = "UNLIT"
    GLASS = "GLASS"

class TextureMap(BaseModel):
    """Reference to a texture asset."""
    uri: str
    channel: str = "rgb"  # which channel to use (rgb, r, g, b, a)
    scale: float = 1.0
    offset: List[float] = [0.0, 0.0]

class PBRMaterial(BaseModel):
    """Physically Based Rendering Material Data."""
    id: str
    name: str
    type: MaterialType = MaterialType.PBR
    
    # Core PBR factors
    base_color: List[float] = [1.0, 1.0, 1.0, 1.0] # RGBA
    metallic: float = 0.0
    roughness: float = 0.5
    emissive_factor: List[float] = [0.0, 0.0, 0.0]

    # Texture Maps (Optional)
    base_color_map: Optional[TextureMap] = None
    metallic_roughness_map: Optional[TextureMap] = None
    normal_map: Optional[TextureMap] = None
    occlusion_map: Optional[TextureMap] = None
    emissive_map: Optional[TextureMap] = None
    
    tags: List[str] = Field(default_factory=list)

class MaterialOpCode(str, Enum):
    CREATE = "CREATE"        # Define a new material
    APPLY_PRESET = "APPLY_PRESET"  # Apply library material to mesh
    PAINT_REGION = "PAINT_REGION"  # Apply material to specific faces

class AgentMaterialInstruction(BaseModel):
    """Atomic token for the Material Engine."""
    op_code: str  # e.g. "APPLY_PRESET"
    params: Dict[str, Union[str, int, float, List[float], List[int]]]
    target_id: Optional[str] = None # ID of the Mesh to paint
