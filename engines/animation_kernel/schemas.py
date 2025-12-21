"""Animation Engine Schemas (The Bones) - Phase 3-4."""
from __future__ import annotations
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

# --- Skeleton Structure ---

class Bone(BaseModel):
    """A single joint in the skeleton hierarchy."""
    id: str
    name: str # e.g. "Head", "Spine", "Leg_L"
    parent_id: Optional[str] = None
    
    # Rest Pose (Bind Pose) - Local Space relative to parent
    head_pos: List[float] = [0.0, 0.0, 0.0] # [x, y, z] Start of bone
    tail_pos: List[float] = [0.0, 1.0, 0.0] # [x, y, z] End of bone (for IK/Vis)
    rotation: List[float] = [0.0, 0.0, 0.0, 1.0] # Quaternion [x, y, z, w]

class Skeleton(BaseModel):
    """A collection of bones."""
    id: str
    bones: List[Bone]
    root_bone_ids: List[str]
    tags: List[str] = Field(default_factory=list)

# --- Animation Data ---

class Keyframe(BaseModel):
    """Bone transform at a specific time."""
    time: float # Seconds
    bone_id: str
    position: Optional[List[float]] = None # [x, y, z]
    rotation: Optional[List[float]] = None # [x, y, z, w] Quaternion
    scale: Optional[List[float]] = None # [x, y, z]

class AnimationClip(BaseModel):
    """A sequence of motion."""
    id: str
    name: str # e.g. "WalkCycle", "Idle"
    duration: float
    tracks: Dict[str, List[Keyframe]] = Field(default_factory=dict) # BoneID -> Keyframes

# --- PHASE AV04: Motion Library & Export ---

class LoopMode(str, Enum):
    """Animation loop behavior."""
    NONE = "none"        # No looping
    LOOP = "loop"        # Standard loop
    PING_PONG = "pingpong"  # Loop forward then backward


class MotionClip(BaseModel):
    """Motion clip with metadata for playback/export."""
    id: str
    name: str
    description: str = ""
    fps: float = 30.0
    duration: float  # Seconds
    loop_mode: LoopMode = LoopMode.LOOP
    bone_tracks: Dict[str, List[Keyframe]] = Field(default_factory=dict)  # bone_id -> keyframes
    action_markers: Dict[str, float] = Field(default_factory=dict)  # event_name -> time
    version: str = "1.0"
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class MotionLibrary(BaseModel):
    """Library of motion clips for avatars."""
    id: str
    name: str
    clips: Dict[str, MotionClip] = Field(default_factory=dict)
    version: str = "1.0"
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class FKIKBoneMask(BaseModel):
    """Bone mask for FK/IK mixing."""
    bone_id: str
    use_ik: bool  # True=IK, False=FK


class AnimationBlend(BaseModel):
    """Blending parameters for transitioning between clips."""
    from_clip_id: str
    to_clip_id: str
    blend_duration: float = 0.5  # Seconds for crossfade
    use_ik_bones: List[str] = Field(default_factory=list)  # Bones to apply IK to
    fk_ik_masks: List[FKIKBoneMask] = Field(default_factory=list)


class ExportMetadata(BaseModel):
    """Metadata for exported avatar."""
    avatar_id: str
    format: str  # "gltf", "usd", etc.
    has_rig: bool = True
    has_meshes: bool = True
    has_morphs: bool = False
    has_materials: bool = False
    has_animations: List[str] = Field(default_factory=list)  # Animation clip IDs
    created_at: datetime = None
    version: str = "1.0"
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.created_at is None:
            self.created_at = datetime.utcnow()


# --- Atomic Operations ---

class AnimOpCode(str, Enum):
    AUTO_RIG = "AUTO_RIG" # Heuristic bone placement
    PLAY_ANIM = "PLAY_ANIM" # Interpolate and output poses
    BIND_MESH = "BIND_MESH" # Calculate skin weights

class AgentAnimInstruction(BaseModel):
    """Atomic token for the Animation Engine."""
    op_code: str # AUTO_RIG, PLAY_ANIM
    params: Dict[str, Any]
    target_skeleton_id: Optional[str] = None
