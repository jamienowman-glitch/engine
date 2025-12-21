"""Data models for Avatar Rig & Attachment Engine (P0-P4)."""
from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from engines.scene_engine.core.geometry import Transform


class AvatarBodyPart(str, Enum):
    HEAD = "HEAD"
    NECK = "NECK"
    TORSO = "TORSO"
    PELVIS = "PELVIS"
    ARM_L_UPPER = "ARM_L_UPPER"
    ARM_L_LOWER = "ARM_L_LOWER"
    HAND_L = "HAND_L"
    ARM_R_UPPER = "ARM_R_UPPER"
    ARM_R_LOWER = "ARM_R_LOWER"
    HAND_R = "HAND_R"
    LEG_L_UPPER = "LEG_L_UPPER"
    LEG_L_LOWER = "LEG_L_LOWER"
    FOOT_L = "FOOT_L"
    LEG_R_UPPER = "LEG_R_UPPER"
    LEG_R_LOWER = "LEG_R_LOWER"
    FOOT_R = "FOOT_R"


class AvatarAttachmentSlot(str, Enum):
    HEAD_TOP = "HEAD_TOP"
    HEAD_FACE_FRONT = "HEAD_FACE_FRONT"
    NECK_BASE = "NECK_BASE"
    HAND_L_GRIP = "HAND_L_GRIP"
    HAND_R_GRIP = "HAND_R_GRIP"
    BACK_MID = "BACK_MID"
    HIP_LEFT = "HIP_LEFT"
    HIP_RIGHT = "HIP_RIGHT"
    FOOT_L_TOP = "FOOT_L_TOP"
    FOOT_R_TOP = "FOOT_R_TOP"


class AvatarBone(BaseModel):
    id: str
    part: AvatarBodyPart
    node_id: str
    parent_id: Optional[str] = None


class AvatarAttachmentBinding(BaseModel):
    slot: AvatarAttachmentSlot
    bone_id: str
    local_transform: Transform


class AvatarRigDefinition(BaseModel):
    bones: List[AvatarBone]
    attachments: List[AvatarAttachmentBinding]
    root_bone_id: str


class PoseDefinition(BaseModel):
    id: str
    name: str
    # Map body part to LOCAL transform (relative to parent bone)
    transforms: Dict[AvatarBodyPart, Transform]


# ===== PHASE AV01: Rig Validation & Morph Targets =====

class RigValidationError(BaseModel):
    """Error report from rig validation."""
    error_code: str  # e.g., "MISSING_BONE", "INVALID_SCALE", "NAN_TRANSFORM"
    bone_id: Optional[str] = None
    message: str


class RigValidationResult(BaseModel):
    """Result of rig validation check."""
    is_valid: bool
    rig_id: str
    errors: List[RigValidationError] = []
    warnings: List[str] = []
    timestamp: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class VertexDelta(BaseModel):
    """Vertex position change for a morph target."""
    vertex_index: int
    delta: List[float]  # [dx, dy, dz]


class MorphTarget(BaseModel):
    """A blendshape/morph target for facial/body variation."""
    id: str
    name: str  # e.g., "smile", "blink_left", "jaw_open"
    mesh_id: str  # Which mesh this morph applies to
    vertex_deltas: List[VertexDelta]  # Vertex indices and position changes
    version: str = "1.0"  # Schema version
    metadata: Dict[str, str] = {}
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def compute_hash(self) -> str:
        """Deterministic hash of morph content."""
        content = f"{self.name}|{self.mesh_id}|{len(self.vertex_deltas)}"
        for vd in sorted(self.vertex_deltas, key=lambda x: x.vertex_index):
            content += f"|{vd.vertex_index}:{vd.delta}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class MorphApplication(BaseModel):
    """Record of applying a morph target to a mesh."""
    morph_id: str
    mesh_id: str
    weight: float = 1.0  # 0.0-1.0 blend factor
    applied_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.applied_at is None:
            self.applied_at = datetime.utcnow()


class RetargetMapping(BaseModel):
    """Mapping from source rig bone to target rig bone."""
    source_bone_id: str
    target_bone_id: str
    mapping_type: str = "humanoid"  # Convention: "humanoid", "custom", etc.


class RetargetRigMap(BaseModel):
    """Complete retarget mapping between two rigs."""
    id: str
    source_rig_id: str
    target_rig_id: str
    mappings: List[RetargetMapping]  # Bone-to-bone mappings
    version: str = "1.0"
    convention: str = "humanoid"  # e.g., "humanoid", "biped", "custom"
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def compute_hash(self) -> str:
        """Deterministic hash of mapping."""
        mappings_str = "|".join([
            f"{m.source_bone_id}→{m.target_bone_id}"
            for m in sorted(self.mappings, key=lambda x: x.source_bone_id)
        ])
        content = f"{self.source_rig_id}|{self.target_rig_id}|{self.convention}|{mappings_str}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


# ===== PHASE AV02: Parametric Avatar Builder =====

class AvatarParamSlider(BaseModel):
    """A single bounded parameter (slider) for avatar customization."""
    name: str  # e.g., "height", "chest_width", "face_width"
    min_value: float
    max_value: float
    default_value: float
    category: str = "body"  # "body", "face", "hair", etc.
    
    def clamp(self, value: float) -> float:
        """Clamp value to [min, max]."""
        return max(self.min_value, min(self.max_value, value))


class AvatarParamSet(BaseModel):
    """Collection of parameter values for an avatar."""
    id: str = None
    values: Dict[str, float] = {}  # param_name -> value
    created_at: datetime = None
    seed: str = "default"  # For deterministic generation
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.id is None:
            self.id = hashlib.sha256(str(self.values).encode()).hexdigest()[:16]
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def compute_hash(self) -> str:
        """Deterministic hash of param values."""
        sorted_items = sorted(self.values.items())
        content = "|".join([f"{k}:{v}" for k, v in sorted_items]) + f"|seed:{self.seed}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class AvatarPreset(BaseModel):
    """A preset configuration for quick avatar generation."""
    id: str
    name: str  # e.g., "casual_male", "fashionable_female"
    description: str = ""
    gender: str = "neutral"  # "male", "female", "neutral", "child"
    style: str = "realistic"  # "realistic", "stylized", "cartoon"
    base_params: Dict[str, float] = {}  # Parameter overrides
    seed: str  # For deterministic generation
    morph_targets: List[str] = []  # Default morphs to apply
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def apply_to_params(self, params: Dict[str, float]) -> Dict[str, float]:
        """Apply preset overrides to parameter set."""
        result = params.copy()
        result.update(self.base_params)
        return result


class AvatarParamHistory(BaseModel):
    """Single entry in the parameter history stack (undo/redo)."""
    timestamp: datetime = None
    param_set: AvatarParamSet = None
    applied_morphs: List[str] = []
    description: str = ""
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class AvatarParamHistory(BaseModel):
    """Single entry in the parameter history stack (undo/redo)."""
    timestamp: datetime = None
    param_set: AvatarParamSet = None
    applied_morphs: List[str] = []
    description: str = ""
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class AvatarBuilder(BaseModel):
    """Main avatar builder state machine."""
    id: str
    param_set: AvatarParamSet  # Current parameters
    history_stack: List[AvatarParamHistory] = []
    max_history_depth: int = 100
    current_morphs: List[str] = []  # Currently applied morphs
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def push_history(self, entry: AvatarParamHistory):
        """Push state to history (undo stack)."""
        self.history_stack.append(entry)
        # Enforce max depth
        while len(self.history_stack) > self.max_history_depth:
            self.history_stack.pop(0)
    
    def pop_history(self) -> Optional[AvatarParamHistory]:
        """Pop state from history (undo)."""
        if self.history_stack:
            return self.history_stack.pop()
        return None

# ===== PHASE AV03: Asset Kits & Materials =====

class KitSlot(str, Enum):
    """Avatar attachment slots for kits."""
    OUTFIT_TOP = "OUTFIT_TOP"
    OUTFIT_BOTTOM = "OUTFIT_BOTTOM"
    OUTFIT_FULL = "OUTFIT_FULL"
    HAIR = "HAIR"
    SHOES = "SHOES"
    ACCESSORIES = "ACCESSORIES"
    BACK_ITEM = "BACK_ITEM"
    HAND_L = "HAND_L"
    HAND_R = "HAND_R"


class KitMetadata(BaseModel):
    """Metadata for an asset kit."""
    kit_id: str
    slot: KitSlot
    name: str
    description: str = ""
    compatible_body_types: List[str] = ["male", "female", "child", "neutral"]
    default_scale: float = 1.0
    default_materials: Dict[str, str] = {}  # material_name -> material_id
    created_at: datetime = None
    version: str = "1.0"
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class KitRegistry(BaseModel):
    """Registry of available asset kits."""
    id: str
    kits: Dict[str, KitMetadata] = {}  # kit_id -> KitMetadata
    version: str = "1.0"
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def register_kit(self, kit: KitMetadata):
        """Register a new kit."""
        self.kits[kit.kit_id] = kit
    
    def get_kit(self, kit_id: str) -> Optional[KitMetadata]:
        """Get kit by ID."""
        return self.kits.get(kit_id)
    
    def list_kits_by_slot(self, slot: KitSlot) -> List[KitMetadata]:
        """List all kits for a given slot."""
        return [kit for kit in self.kits.values() if kit.slot == slot]


class KitAttachment(BaseModel):
    """Record of attaching a kit to an avatar."""
    kit_id: str
    slot: KitSlot
    body_type: str  # "male", "female", "child", "neutral"
    scale: float = 1.0  # Scale factor
    position: List[float] = [0.0, 0.0, 0.0]  # Offset [x, y, z]
    rotation: List[float] = [0.0, 0.0, 0.0]  # Euler angles [x, y, z]
    applied_materials: Dict[str, str] = {}  # face_id -> material_id
    applied_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.applied_at is None:
            self.applied_at = datetime.utcnow()


class UVValidationResult(BaseModel):
    """Result of UV/texel density validation."""
    is_valid: bool
    mesh_id: str
    texel_density: float  # Texels per unit
    overlap_detected: bool = False
    warnings: List[str] = []
    errors: List[str] = []


class MaterialPreset(BaseModel):
    """Material preset for quick application."""
    id: str
    name: str
    description: str = ""
    properties: Dict[str, Any] = {}  # material_property -> value
    version: str = "1.0"
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.created_at is None:
            self.created_at = datetime.utcnow()