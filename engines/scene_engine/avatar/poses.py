"""Avatar Pose Engine (P1).

Provides the PoseLibrary and utilities to apply named poses to avatars.
"""
from __future__ import annotations

from typing import Dict, Optional

from engines.scene_engine.avatar.models import (
    AvatarBodyPart,
    AvatarRigDefinition,
    PoseDefinition,
)
from engines.scene_engine.avatar.service import apply_avatar_pose
from engines.scene_engine.core.geometry import EulerAngles, Transform, Vector3
from engines.scene_engine.core.scene_v2 import SceneV2


def _rot(x, y, z) -> EulerAngles:
    return EulerAngles(x=float(x), y=float(y), z=float(z))

def _vec(x, y, z) -> Vector3:
    return Vector3(x=float(x), y=float(y), z=float(z))

def _t_rot(x, y, z) -> Transform:
    """Helper for rotation-only local transform (common for bones)."""
    return Transform(
        position=_vec(0, 0, 0),
        rotation=_rot(x, y, z),
        scale=_vec(1, 1, 1)
    )


class PoseLibrary:
    """Registry of standard avatar poses."""
    
    # Standard Poses
    IDLE = PoseDefinition(
        id="pose_idle",
        name="Idle",
        transforms={
            # Slight relaxation
            AvatarBodyPart.ARM_L_UPPER: _t_rot(0, 0, -10), # Slight outward
            AvatarBodyPart.ARM_R_UPPER: _t_rot(0, 0, 10),
            AvatarBodyPart.ARM_L_LOWER: _t_rot(0, 0, 0), # Straight-ish
            AvatarBodyPart.ARM_R_LOWER: _t_rot(0, 0, 0),
        }
    )

    TALK = PoseDefinition(
        id="pose_talk",
        name="Talk",
        transforms={
            AvatarBodyPart.ARM_L_UPPER: _t_rot(0, 0, -20),
            AvatarBodyPart.ARM_L_LOWER: _t_rot(45, 0, 0), # Bend elbow forward/up
            AvatarBodyPart.ARM_R_UPPER: _t_rot(0, 0, 20),
            AvatarBodyPart.ARM_R_LOWER: _t_rot(45, 0, 0),
        }
    )

    POINT = PoseDefinition(
        id="pose_point",
        name="Point",
        transforms={
            AvatarBodyPart.ARM_R_UPPER: _t_rot(0, 0, 80), # Raise arm
            AvatarBodyPart.ARM_R_LOWER: _t_rot(10, 0, 0), # Slight bend
            # Hand binding would be handled by prop usually, or specific hand logic later
        }
    )

    SIT = PoseDefinition(
        id="pose_sit",
        name="Sit",
        transforms={
            AvatarBodyPart.PELVIS: Transform(position=_vec(0, -0.4, 0), rotation=_rot(0,0,0), scale=_vec(1,1,1)), # Drop hips
            AvatarBodyPart.LEG_L_UPPER: _t_rot(90, 0, 0), # Leg forward
            AvatarBodyPart.LEG_L_LOWER: _t_rot(-90, 0, 0), # Knee down
            AvatarBodyPart.LEG_R_UPPER: _t_rot(90, 0, 0),
            AvatarBodyPart.LEG_R_LOWER: _t_rot(-90, 0, 0),
        }
    )
    
    WALK_START = PoseDefinition(
        id="pose_walk_start",
        name="Walk Start",
        transforms={
             AvatarBodyPart.LEG_L_UPPER: _t_rot(20, 0, 0),
             AvatarBodyPart.LEG_R_UPPER: _t_rot(-20, 0, 0),
             AvatarBodyPart.ARM_L_UPPER: _t_rot(-20, 0, 0),
             AvatarBodyPart.ARM_R_UPPER: _t_rot(20, 0, 0),
        }
    )

    _registry = {
        IDLE.id: IDLE,
        TALK.id: TALK,
        POINT.id: POINT,
        SIT.id: SIT,
        WALK_START.id: WALK_START
    }

    @classmethod
    def get(cls, pose_id: str) -> Optional[PoseDefinition]:
        return cls._registry.get(pose_id)

    @classmethod
    def list_poses(cls) -> Dict[str, str]:
        return {p.id: p.name for p in cls._registry.values()}


def apply_pose(
    scene_in: SceneV2,
    rig: AvatarRigDefinition,
    pose_id: str
) -> SceneV2:
    """Applies a named pose from the library to the avatar."""
    pose = PoseLibrary.get(pose_id)
    if not pose:
        # P0 behavior: warn or ignore?
        # Let's ignore for robustness or raise?
        # Specification implies "apply_pose(scene, pose_id)".
        # We'll assume valid ID. If invalid, we return scene unchanged for safety.
        # Ideally logging a warning.
        return scene_in

    return apply_avatar_pose(scene_in, rig, pose.transforms)
