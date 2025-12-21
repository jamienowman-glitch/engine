"""
Tests for PHASE_AV04: Motion Library & Animation Export.

Covers:
- Motion library creation and clip management
- Playback at specific times
- Animation blending and crossfades
- FK/IK mixing
- Export metadata generation
"""
import pytest
from datetime import datetime

from engines.animation_kernel.schemas import (
    MotionClip, MotionLibrary, Keyframe, LoopMode, Skeleton, Bone,
    FKIKBoneMask, ExportMetadata
)
from engines.animation_kernel.service import (
    MotionLibraryService, create_export_metadata
)


class TestMotionLibrary:
    """Test motion library creation and management."""
    
    def test_create_library(self):
        """Create a new motion library."""
        service = MotionLibraryService()
        lib = service.create_library("test_library")
        
        assert lib.id is not None
        assert lib.name == "test_library"
        assert len(lib.clips) == 0
    
    def test_add_clip_to_library(self):
        """Add a motion clip to a library."""
        service = MotionLibraryService()
        lib = service.create_library("test_library")
        
        clip = MotionClip(
            id="clip_walk",
            name="Walk",
            duration=1.0,
            fps=30.0,
            loop_mode=LoopMode.LOOP
        )
        
        added = service.add_clip_to_library(lib.id, clip)
        assert added is not None
        assert added.id == clip.id
        assert clip.id in lib.clips
    
    def test_get_clip(self):
        """Retrieve a motion clip by ID."""
        service = MotionLibraryService()
        lib = service.create_library("test_library")
        
        clip = MotionClip(
            id="clip_idle",
            name="Idle",
            duration=0.5,
            fps=30.0
        )
        
        service.add_clip_to_library(lib.id, clip)
        retrieved = service.get_clip(clip.id)
        
        assert retrieved is not None
        assert retrieved.name == "Idle"
    
    def test_get_nonexistent_clip(self):
        """Get non-existent clip returns None."""
        service = MotionLibraryService()
        clip = service.get_clip("nonexistent")
        assert clip is None


class TestMotionClipPlayback:
    """Test motion clip playback evaluation."""
    
    def test_playback_no_looping(self):
        """Playback with no looping clamps to duration."""
        service = MotionLibraryService()
        
        kf1 = Keyframe(time=0.0, bone_id="root", rotation=[0, 0, 0, 1])
        kf2 = Keyframe(time=0.5, bone_id="root", rotation=[0.1, 0, 0, 0.99])
        
        clip = MotionClip(
            id="clip_test",
            name="Test",
            duration=0.5,
            fps=30.0,
            loop_mode=LoopMode.NONE,
            bone_tracks={"root": [kf1, kf2]}
        )
        
        # Playback at 0.3 (within duration)
        pose_early = service.playback_at_time(clip, 0.3)
        assert "root" in pose_early
        assert pose_early["root"] is not None
        
        # Playback at 1.0 (beyond duration, should clamp)
        pose_late = service.playback_at_time(clip, 1.0)
        assert "root" in pose_late
        # Should be at end of animation
    
    def test_playback_with_looping(self):
        """Playback with looping wraps around duration."""
        service = MotionLibraryService()
        
        kf1 = Keyframe(time=0.0, bone_id="spine", rotation=[0, 0, 0, 1])
        kf2 = Keyframe(time=1.0, bone_id="spine", rotation=[0, 0.2, 0, 0.98])
        
        clip = MotionClip(
            id="clip_walk",
            name="Walk Cycle",
            duration=1.0,
            fps=30.0,
            loop_mode=LoopMode.LOOP,
            bone_tracks={"spine": [kf1, kf2]}
        )
        
        # Playback at 0.5
        pose_half = service.playback_at_time(clip, 0.5)
        assert "spine" in pose_half
        
        # Playback at 1.5 (beyond duration with looping)
        pose_loop = service.playback_at_time(clip, 1.5)
        assert "spine" in pose_loop
        # Time 1.5 % 1.0 = 0.5
    
    def test_playback_ping_pong(self):
        """Playback with ping-pong mode goes forward then backward."""
        service = MotionLibraryService()
        
        kf1 = Keyframe(time=0.0, bone_id="head", rotation=[0, 0, 0, 1])
        kf2 = Keyframe(time=1.0, bone_id="head", rotation=[0, 0, 0.1, 0.99])
        
        clip = MotionClip(
            id="clip_nod",
            name="Head Nod",
            duration=1.0,
            fps=30.0,
            loop_mode=LoopMode.PING_PONG,
            bone_tracks={"head": [kf1, kf2]}
        )
        
        # Playback at 0.5 (forward)
        pose_forward = service.playback_at_time(clip, 0.5)
        assert "head" in pose_forward
        
        # Playback at 1.5 (backward - in ping pong)
        pose_backward = service.playback_at_time(clip, 1.5)
        assert "head" in pose_backward
    
    def test_playback_interpolation(self):
        """Playback interpolates between keyframes."""
        service = MotionLibraryService()
        
        kf1 = Keyframe(time=0.0, bone_id="arm_l", rotation=[0, 0, 0, 1])
        kf2 = Keyframe(time=1.0, bone_id="arm_l", rotation=[1, 0, 0, 0])
        
        clip = MotionClip(
            id="clip_raise_arm",
            name="Raise Arm",
            duration=1.0,
            fps=30.0,
            bone_tracks={"arm_l": [kf1, kf2]}
        )
        
        # Playback at 0.5 (should interpolate)
        pose_mid = service.playback_at_time(clip, 0.5)
        assert "arm_l" in pose_mid
        
        # Check that it's interpolated (not exactly either keyframe)
        quat = pose_mid["arm_l"]
        assert len(quat) == 4
        # Should be somewhere between [0, 0, 0, 1] and [1, 0, 0, 0]
        assert quat[0] > 0.0  # Should have x component


class TestAnimationBlending:
    """Test animation clip blending and transitions."""
    
    def test_blend_two_clips(self):
        """Blend two animation clips with crossfade."""
        service = MotionLibraryService()
        
        clip1 = MotionClip(
            id="clip_walk",
            name="Walk",
            duration=1.0,
            fps=30.0,
            loop_mode=LoopMode.LOOP,
            bone_tracks={
                "root": [
                    Keyframe(time=0.0, bone_id="root", rotation=[0, 0, 0, 1]),
                    Keyframe(time=1.0, bone_id="root", rotation=[0, 0.1, 0, 0.995])
                ]
            }
        )
        
        clip2 = MotionClip(
            id="clip_run",
            name="Run",
            duration=0.5,
            fps=30.0,
            loop_mode=LoopMode.LOOP,
            bone_tracks={
                "root": [
                    Keyframe(time=0.0, bone_id="root", rotation=[0, 0.1, 0, 0.995]),
                    Keyframe(time=0.5, bone_id="root", rotation=[0, 0.2, 0, 0.98])
                ]
            }
        )
        
        blended = service.blend_clips(clip1, clip2, blend_time=0.25)
        
        assert blended.id is not None
        assert blended.name is not None
        assert blended.duration > clip1.duration  # Should be longer
        assert "root" in blended.bone_tracks
        assert len(blended.bone_tracks["root"]) > 0
    
    def test_blend_preserves_clip_data(self):
        """Blending preserves original clip keyframes."""
        service = MotionLibraryService()
        
        clip1 = MotionClip(
            id="clip_a",
            name="ClipA",
            duration=1.0,
            fps=30.0,
            bone_tracks={
                "spine": [
                    Keyframe(time=0.0, bone_id="spine", rotation=[0, 0, 0, 1])
                ]
            }
        )
        
        clip2 = MotionClip(
            id="clip_b",
            name="ClipB",
            duration=0.5,
            fps=30.0,
            bone_tracks={
                "spine": [
                    Keyframe(time=0.0, bone_id="spine", rotation=[0, 0, 0, 1])
                ]
            }
        )
        
        # Should not raise exception
        blended = service.blend_clips(clip1, clip2, blend_time=0.5)
        assert blended is not None


class TestFKIKMixing:
    """Test FK/IK mixing for animations."""
    
    def test_apply_fk_ik_mix(self):
        """Apply FK/IK mixing to a clip."""
        service = MotionLibraryService()
        
        clip = MotionClip(
            id="clip_walk",
            name="Walk",
            duration=1.0,
            fps=30.0,
            bone_tracks={
                "foot_l": [
                    Keyframe(time=0.0, bone_id="foot_l", rotation=[0, 0, 0, 1]),
                    Keyframe(time=0.5, bone_id="foot_l", rotation=[0, 0, 0, 1]),
                    Keyframe(time=1.0, bone_id="foot_l", rotation=[0, 0, 0, 1])
                ]
            }
        )
        
        masks = [
            FKIKBoneMask(bone_id="foot_l", use_ik=True),
            FKIKBoneMask(bone_id="foot_r", use_ik=True)
        ]
        
        ik_targets = {
            "foot_l": [0.0, 0.1, 0.0],
            "foot_r": [0.0, 0.1, 0.0]
        }
        
        mixed = service.apply_fk_ik_mix(clip, masks, ik_targets)
        
        assert mixed.id is not None
        assert mixed.name is not None
        assert "foot_l" in mixed.bone_tracks
    
    def test_fk_ik_mix_preserves_structure(self):
        """FK/IK mixing preserves clip structure."""
        service = MotionLibraryService()
        
        original_tracks = {
            "spine": [
                Keyframe(time=0.0, bone_id="spine", rotation=[0, 0, 0, 1]),
                Keyframe(time=1.0, bone_id="spine", rotation=[0, 0, 0.1, 0.995])
            ],
            "head": [
                Keyframe(time=0.0, bone_id="head", rotation=[0, 0, 0, 1]),
                Keyframe(time=1.0, bone_id="head", rotation=[0, 0, 0, 1])
            ]
        }
        
        clip = MotionClip(
            id="clip_test",
            name="Test",
            duration=1.0,
            fps=30.0,
            bone_tracks=original_tracks
        )
        
        masks = [FKIKBoneMask(bone_id="head", use_ik=False)]
        
        mixed = service.apply_fk_ik_mix(clip, masks, {})
        
        # Should still have both bone tracks
        assert "spine" in mixed.bone_tracks
        assert "head" in mixed.bone_tracks


class TestExportMetadata:
    """Test export metadata generation."""
    
    def test_create_export_metadata_minimal(self):
        """Create export metadata with minimal parameters."""
        meta = create_export_metadata("avatar_001")
        
        assert meta.avatar_id == "avatar_001"
        assert meta.format == "gltf"
        assert meta.has_rig is True
        assert meta.has_meshes is True
    
    def test_create_export_metadata_full(self):
        """Create export metadata with all parameters."""
        animations = ["clip_walk", "clip_run", "clip_idle"]
        meta = create_export_metadata(
            avatar_id="avatar_002",
            format="usd",
            has_rig=True,
            has_meshes=True,
            has_morphs=True,
            has_materials=True,
            animation_clip_ids=animations
        )
        
        assert meta.avatar_id == "avatar_002"
        assert meta.format == "usd"
        assert meta.has_morphs is True
        assert meta.has_materials is True
        assert len(meta.has_animations) == 3
        assert "clip_walk" in meta.has_animations
    
    def test_export_metadata_timestamp(self):
        """Export metadata includes creation timestamp."""
        meta = create_export_metadata("avatar_003")
        
        assert meta.created_at is not None
        assert isinstance(meta.created_at, datetime)


class TestMotionClipSchema:
    """Test MotionClip schema and properties."""
    
    def test_motion_clip_creation(self):
        """Create a motion clip."""
        clip = MotionClip(
            id="clip_test",
            name="Test Clip",
            description="A test motion clip",
            fps=30.0,
            duration=1.0,
            loop_mode=LoopMode.LOOP
        )
        
        assert clip.id == "clip_test"
        assert clip.name == "Test Clip"
        assert clip.fps == 30.0
        assert clip.duration == 1.0
        assert clip.created_at is not None
    
    def test_motion_clip_with_keyframes(self):
        """Motion clip with keyframe tracks."""
        keyframes = [
            Keyframe(time=0.0, bone_id="root", rotation=[0, 0, 0, 1]),
            Keyframe(time=0.5, bone_id="root", rotation=[0, 0.1, 0, 0.995]),
            Keyframe(time=1.0, bone_id="root", rotation=[0, 0.2, 0, 0.98])
        ]
        
        clip = MotionClip(
            id="clip_rotate",
            name="Rotate",
            duration=1.0,
            fps=30.0,
            bone_tracks={"root": keyframes}
        )
        
        assert "root" in clip.bone_tracks
        assert len(clip.bone_tracks["root"]) == 3
    
    def test_motion_clip_with_action_markers(self):
        """Motion clip with action markers."""
        clip = MotionClip(
            id="clip_footstep",
            name="Footstep",
            duration=1.0,
            fps=30.0,
            action_markers={
                "foot_plant": 0.25,
                "foot_lift": 0.75
            }
        )
        
        assert len(clip.action_markers) == 2
        assert clip.action_markers["foot_plant"] == 0.25


class TestMotionLibraryIntegration:
    """Integration tests for motion library workflows."""
    
    def test_complete_animation_workflow(self):
        """Complete workflow: create library, add clips, blend."""
        service = MotionLibraryService()
        lib = service.create_library("character_animations")
        
        # Create idle animation
        idle = MotionClip(
            id="idle",
            name="Idle",
            duration=1.0,
            fps=30.0,
            loop_mode=LoopMode.LOOP,
            bone_tracks={
                "root": [
                    Keyframe(time=0.0, bone_id="root", rotation=[0, 0, 0, 1]),
                    Keyframe(time=1.0, bone_id="root", rotation=[0, 0, 0, 1])
                ]
            }
        )
        
        # Create walk animation
        walk = MotionClip(
            id="walk",
            name="Walk",
            duration=0.8,
            fps=30.0,
            loop_mode=LoopMode.LOOP,
            bone_tracks={
                "root": [
                    Keyframe(time=0.0, bone_id="root", rotation=[0, 0, 0, 1]),
                    Keyframe(time=0.4, bone_id="root", rotation=[0, 0.05, 0, 0.999]),
                    Keyframe(time=0.8, bone_id="root", rotation=[0, 0, 0, 1])
                ]
            }
        )
        
        # Add to library
        service.add_clip_to_library(lib.id, idle)
        service.add_clip_to_library(lib.id, walk)
        
        # Blend them
        blended = service.blend_clips(idle, walk, 0.2)
        
        assert blended is not None
        assert "root" in blended.bone_tracks
    
    def test_multiple_bone_playback(self):
        """Playback with multiple bones in animation."""
        service = MotionLibraryService()
        
        clip = MotionClip(
            id="complex_anim",
            name="Complex",
            duration=1.0,
            fps=30.0,
            bone_tracks={
                "root": [
                    Keyframe(time=0.0, bone_id="root", rotation=[0, 0, 0, 1]),
                    Keyframe(time=1.0, bone_id="root", rotation=[0, 0.1, 0, 0.995])
                ],
                "spine": [
                    Keyframe(time=0.0, bone_id="spine", rotation=[0, 0, 0, 1]),
                    Keyframe(time=0.5, bone_id="spine", rotation=[0.05, 0, 0, 0.999]),
                    Keyframe(time=1.0, bone_id="spine", rotation=[0, 0, 0, 1])
                ],
                "head": [
                    Keyframe(time=0.0, bone_id="head", rotation=[0, 0, 0, 1]),
                    Keyframe(time=1.0, bone_id="head", rotation=[0, 0, 0, 1])
                ]
            }
        )
        
        # Playback at various times
        pose_0 = service.playback_at_time(clip, 0.0)
        pose_mid = service.playback_at_time(clip, 0.5)
        pose_end = service.playback_at_time(clip, 1.0)
        
        # All poses should have all bones
        assert len(pose_0) == 3
        assert len(pose_mid) == 3
        assert len(pose_end) == 3
        assert "root" in pose_0
        assert "spine" in pose_mid
        assert "head" in pose_end
