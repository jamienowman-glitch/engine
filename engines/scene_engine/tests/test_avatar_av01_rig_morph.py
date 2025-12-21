"""
Tests for PHASE_AV01: Rig & Morph Foundations.

Covers:
- Rig schema validation
- Morph target application
- Retarget mapping determinism
- IK input validation
"""
import pytest
from datetime import datetime

from engines.scene_engine.avatar.models import (
    AvatarBodyPart,
    AvatarBone,
    AvatarRigDefinition,
    RigValidationResult,
    MorphTarget,
    VertexDelta,
    MorphApplication,
    RetargetRigMap,
    RetargetMapping,
)
from engines.scene_engine.avatar.service import (
    validate_rig,
    apply_morph,
    create_retarget_mapping,
)
from engines.animation_kernel.service import (
    validate_ik_input,
    validate_skeleton,
    AnimationService,
)
from engines.animation_kernel.schemas import Skeleton, Bone


class TestRigValidation:
    """Test rig schema validation."""
    
    def test_valid_rig(self):
        """Valid rig should pass validation."""
        root = AvatarBone(
            id="root",
            part=AvatarBodyPart.PELVIS,
            node_id="node_root",
            parent_id=None
        )
        spine = AvatarBone(
            id="spine",
            part=AvatarBodyPart.TORSO,
            node_id="node_spine",
            parent_id="root"
        )
        head = AvatarBone(
            id="head",
            part=AvatarBodyPart.HEAD,
            node_id="node_head",
            parent_id="spine"
        )
        
        rig = AvatarRigDefinition(
            bones=[root, spine, head],
            attachments=[],
            root_bone_id="root"
        )
        
        result = validate_rig(rig)
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_missing_root_bone(self):
        """Validation should fail if root bone doesn't exist."""
        root = AvatarBone(
            id="root",
            part=AvatarBodyPart.PELVIS,
            node_id="node_root"
        )
        
        rig = AvatarRigDefinition(
            bones=[root],
            attachments=[],
            root_bone_id="nonexistent"
        )
        
        result = validate_rig(rig)
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "MISSING_ROOT"
    
    def test_invalid_parent_reference(self):
        """Validation should fail if parent bone is missing."""
        root = AvatarBone(
            id="root",
            part=AvatarBodyPart.PELVIS,
            node_id="node_root"
        )
        orphan = AvatarBone(
            id="orphan",
            part=AvatarBodyPart.HEAD,
            node_id="node_orphan",
            parent_id="nonexistent"
        )
        
        rig = AvatarRigDefinition(
            bones=[root, orphan],
            attachments=[],
            root_bone_id="root"
        )
        
        result = validate_rig(rig)
        assert not result.is_valid
        assert any(e.error_code == "MISSING_PARENT" for e in result.errors)
    
    def test_duplicate_bone_ids(self):
        """Validation should detect duplicate bone IDs."""
        bone1 = AvatarBone(
            id="dup",
            part=AvatarBodyPart.HEAD,
            node_id="node1"
        )
        bone2 = AvatarBone(
            id="dup",
            part=AvatarBodyPart.TORSO,
            node_id="node2"
        )
        
        rig = AvatarRigDefinition(
            bones=[bone1, bone2],
            attachments=[],
            root_bone_id="dup"
        )
        
        result = validate_rig(rig)
        assert not result.is_valid
        assert any(e.error_code == "DUPLICATE_BONE_ID" for e in result.errors)


class TestMorphTargets:
    """Test morph target application."""
    
    def test_apply_morph_basic(self):
        """Applying a morph should modify vertices predictably."""
        vertices = [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ]
        
        morph = MorphTarget(
            id="smile",
            name="smile",
            mesh_id="mesh_face",
            vertex_deltas=[
                VertexDelta(vertex_index=0, delta=[0.1, 0.0, 0.0]),
                VertexDelta(vertex_index=2, delta=[0.0, -0.1, 0.0]),
            ]
        )
        
        result_vertices, app = apply_morph(vertices, morph, weight=1.0)
        
        # Check vertex 0 moved
        assert result_vertices[0][0] == pytest.approx(0.1)
        # Check vertex 1 unchanged
        assert result_vertices[1] == vertices[1]
        # Check vertex 2 moved
        assert result_vertices[2][1] == pytest.approx(0.9)
        
        # Check application record
        assert app.morph_id == "smile"
        assert app.weight == 1.0
    
    def test_apply_morph_with_weight(self):
        """Morph weight should scale deltas."""
        vertices = [[0.0, 0.0, 0.0]]
        
        morph = MorphTarget(
            id="blink",
            name="blink",
            mesh_id="mesh_eye",
            vertex_deltas=[
                VertexDelta(vertex_index=0, delta=[1.0, 1.0, 1.0]),
            ]
        )
        
        result_vertices, _ = apply_morph(vertices, morph, weight=0.5)
        
        # Delta should be scaled by weight
        assert result_vertices[0][0] == pytest.approx(0.5)
        assert result_vertices[0][1] == pytest.approx(0.5)
        assert result_vertices[0][2] == pytest.approx(0.5)
    
    def test_apply_morph_weight_clamping(self):
        """Weight should be clamped to [0, 1]."""
        vertices = [[0.0, 0.0, 0.0]]
        
        morph = MorphTarget(
            id="test",
            name="test",
            mesh_id="mesh_test",
            vertex_deltas=[
                VertexDelta(vertex_index=0, delta=[2.0, 0.0, 0.0]),
            ]
        )
        
        # Test weight > 1 gets clamped
        result_vertices, _ = apply_morph(vertices, morph, weight=2.0)
        assert result_vertices[0][0] == pytest.approx(2.0)  # Clamped to 1.0, so delta is 2.0 * 1.0
        
        # Test negative weight clamped to 0
        result_vertices, _ = apply_morph(vertices, morph, weight=-1.0)
        assert result_vertices[0][0] == pytest.approx(0.0)
    
    def test_morph_determinism(self):
        """Same morph + weight should produce same output."""
        vertices = [
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
        ]
        
        morph = MorphTarget(
            id="det_test",
            name="det_test",
            mesh_id="mesh_test",
            vertex_deltas=[
                VertexDelta(vertex_index=0, delta=[0.123, -0.456, 0.789]),
                VertexDelta(vertex_index=1, delta=[-0.1, -0.2, -0.3]),
            ]
        )
        
        # Apply twice
        result1, _ = apply_morph(vertices, morph, weight=0.75)
        result2, _ = apply_morph(vertices, morph, weight=0.75)
        
        # Results should be identical
        for i in range(len(result1)):
            for j in range(3):
                assert result1[i][j] == pytest.approx(result2[i][j])
    
    def test_morph_hash_determinism(self):
        """Morph hash should be deterministic."""
        morph1 = MorphTarget(
            id="hash_test_1",
            name="smile",
            mesh_id="face",
            vertex_deltas=[
                VertexDelta(vertex_index=0, delta=[0.1, 0.0, 0.0]),
                VertexDelta(vertex_index=5, delta=[0.0, 0.1, 0.0]),
            ]
        )
        
        morph2 = MorphTarget(
            id="hash_test_2",
            name="smile",
            mesh_id="face",
            vertex_deltas=[
                VertexDelta(vertex_index=0, delta=[0.1, 0.0, 0.0]),
                VertexDelta(vertex_index=5, delta=[0.0, 0.1, 0.0]),
            ]
        )
        
        # Same content -> same hash (ignoring ID)
        hash1 = morph1.compute_hash()
        hash2 = morph2.compute_hash()
        assert hash1 == hash2
        
        # Different content -> different hash
        morph3 = MorphTarget(
            id="hash_test_3",
            name="frown",
            mesh_id="face",
            vertex_deltas=[
                VertexDelta(vertex_index=0, delta=[0.1, 0.0, 0.0]),
            ]
        )
        hash3 = morph3.compute_hash()
        assert hash3 != hash1


class TestRetargetMapping:
    """Test retarget mapping."""
    
    def test_create_retarget_mapping_identity(self):
        """Creating mapping with identical rigs should map bones by ID."""
        root = AvatarBone(
            id="root",
            part=AvatarBodyPart.PELVIS,
            node_id="node_root"
        )
        spine = AvatarBone(
            id="spine",
            part=AvatarBodyPart.TORSO,
            node_id="node_spine",
            parent_id="root"
        )
        
        rig = AvatarRigDefinition(
            bones=[root, spine],
            attachments=[],
            root_bone_id="root"
        )
        
        mapping = create_retarget_mapping(rig, rig)
        
        # All bones should be mapped to themselves
        assert len(mapping.mappings) == 2
        for m in mapping.mappings:
            assert m.source_bone_id == m.target_bone_id
    
    def test_retarget_mapping_determinism(self):
        """Retarget mapping should be deterministic."""
        root = AvatarBone(id="root", part=AvatarBodyPart.PELVIS, node_id="node_root")
        spine = AvatarBone(id="spine", part=AvatarBodyPart.TORSO, node_id="node_spine", parent_id="root")
        
        rig = AvatarRigDefinition(bones=[root, spine], attachments=[], root_bone_id="root")
        
        # Create mapping twice
        mapping1 = create_retarget_mapping(rig, rig)
        mapping2 = create_retarget_mapping(rig, rig)
        
        # Hashes should be equal
        hash1 = mapping1.compute_hash()
        hash2 = mapping2.compute_hash()
        assert hash1 == hash2
    
    def test_retarget_with_custom_mappings(self):
        """Custom mapping overrides should work."""
        root1 = AvatarBone(id="root_src", part=AvatarBodyPart.PELVIS, node_id="node_root_src")
        head1 = AvatarBone(id="head_src", part=AvatarBodyPart.HEAD, node_id="node_head_src", parent_id="root_src")
        
        rig_src = AvatarRigDefinition(bones=[root1, head1], attachments=[], root_bone_id="root_src")
        
        root2 = AvatarBone(id="root_tgt", part=AvatarBodyPart.PELVIS, node_id="node_root_tgt")
        head2 = AvatarBone(id="head_tgt", part=AvatarBodyPart.HEAD, node_id="node_head_tgt", parent_id="root_tgt")
        
        rig_tgt = AvatarRigDefinition(bones=[root2, head2], attachments=[], root_bone_id="root_tgt")
        
        # Custom mapping
        custom = {"head_src": "head_tgt"}
        mapping = create_retarget_mapping(rig_src, rig_tgt, custom_mappings=custom)
        
        # Check mapping
        head_mapping = next((m for m in mapping.mappings if m.source_bone_id == "head_src"), None)
        assert head_mapping is not None
        assert head_mapping.target_bone_id == "head_tgt"


class TestIKValidation:
    """Test IK input validation."""
    
    def test_valid_ik_input(self):
        """Valid IK input should return None."""
        error = validate_ik_input(
            root_pos=[0.0, 0.0, 0.0],
            target_pos=[1.0, 0.0, 0.0],
            l1=0.5,
            l2=0.5
        )
        assert error is None
    
    def test_invalid_root_pos_format(self):
        """Invalid root_pos format should be caught."""
        error = validate_ik_input(
            root_pos=[0.0, 0.0],  # Only 2 elements
            target_pos=[1.0, 0.0, 0.0],
            l1=0.5,
            l2=0.5
        )
        assert error is not None
        assert "root_pos" in error
    
    def test_invalid_target_pos_format(self):
        """Invalid target_pos format should be caught."""
        error = validate_ik_input(
            root_pos=[0.0, 0.0, 0.0],
            target_pos=[1.0, 0.0],  # Only 2 elements
            l1=0.5,
            l2=0.5
        )
        assert error is not None
        assert "target_pos" in error
    
    def test_nan_in_positions(self):
        """NaN in positions should be caught."""
        import math
        error = validate_ik_input(
            root_pos=[0.0, math.nan, 0.0],
            target_pos=[1.0, 0.0, 0.0],
            l1=0.5,
            l2=0.5
        )
        assert error is not None
        assert "NaN" in error
    
    def test_invalid_bone_lengths(self):
        """Invalid bone lengths should be caught."""
        error = validate_ik_input(
            root_pos=[0.0, 0.0, 0.0],
            target_pos=[1.0, 0.0, 0.0],
            l1=0.0,  # Invalid
            l2=0.5
        )
        assert error is not None
        assert "positive" in error.lower() or "length" in error.lower()
    
    def test_negative_bone_lengths(self):
        """Negative bone lengths should be caught."""
        error = validate_ik_input(
            root_pos=[0.0, 0.0, 0.0],
            target_pos=[1.0, 0.0, 0.0],
            l1=-0.5,
            l2=0.5
        )
        assert error is not None


class TestSkeletonValidation:
    """Test skeleton validation."""
    
    def test_valid_skeleton(self):
        """Valid skeleton should pass validation."""
        root = Bone(id="root", name="Root")
        spine = Bone(id="spine", name="Spine", parent_id="root")
        
        skeleton = Skeleton(id="skel_1", bones=[root, spine], root_bone_ids=["root"])
        
        error = validate_skeleton(skeleton)
        assert error is None
    
    def test_empty_skeleton(self):
        """Empty skeleton should fail."""
        skeleton = Skeleton(id="skel_empty", bones=[], root_bone_ids=["root"])
        
        error = validate_skeleton(skeleton)
        assert error is not None
        assert "no bones" in error.lower()
    
    def test_missing_root_bone_skeleton(self):
        """Missing root bone should fail."""
        spine = Bone(id="spine", name="Spine")
        
        skeleton = Skeleton(id="skel_2", bones=[spine], root_bone_ids=["root"])
        
        error = validate_skeleton(skeleton)
        assert error is not None
        assert "root" in error.lower()
    
    def test_invalid_parent_ref_skeleton(self):
        """Invalid parent reference should fail."""
        spine = Bone(id="spine", name="Spine", parent_id="nonexistent")
        
        skeleton = Skeleton(id="skel_3", bones=[spine], root_bone_ids=["spine"])
        
        error = validate_skeleton(skeleton)
        assert error is not None
        assert "parent" in error.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
