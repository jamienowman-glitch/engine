"""Animation Engine Tests (Phase 3-4)."""
import pytest
from engines.animation_kernel.service import AnimationService, validate_skeleton, validate_ik_input
from engines.animation_kernel.schemas import AgentAnimInstruction, Skeleton, Bone

def test_auto_rig():
    service = AnimationService()
    
    # 1. Auto Rig (Create Humanoid with 15 bones)
    instr = AgentAnimInstruction(op_code="AUTO_RIG", params={})
    skeleton = service.execute_instruction(instr)
    
    assert skeleton is not None
    assert len(skeleton.bones) == 15  # Full humanoid: root, spine, head, shoulders, arms, forearms, thighs, calves, feet
    assert skeleton.bones[0].id == "root"
    assert skeleton.bones[1].parent_id == "root"

def test_play_anim():
    service = AnimationService()
    skeleton = service.execute_instruction(AgentAnimInstruction(op_code="AUTO_RIG", params={}))
    
    # 2. Play Walk Cycle at t=0.25 (Quarter turn)
    instr = AgentAnimInstruction(
        op_code="PLAY_ANIM",
        params={"clip_name": "WALK", "time": 0.25},
        target_skeleton_id=skeleton.id
    )
    
    pose = service.execute_instruction(instr)
    assert pose is not None
    assert "root" in pose
    # Check Math: sin(0.25*2pi) = sin(pi/2) = 1.0
    # Angle = 0.1 * 1.0 = 0.1 rad
    # qw = cos(0.05) ~ .998
    # qy = sin(0.05) ~ .0499
    quat = pose["root"]
    assert len(quat) == 4
    assert quat[1] > 0.04 # qy check


# ===== PHASE AV01: Validation Tests =====

class TestSkeletonValidation:
    """Test skeleton validation (AV01)."""
    
    def test_valid_skeleton(self):
        """Valid skeleton should pass validation."""
        root = Bone(id="root", name="Root")
        spine = Bone(id="spine", name="Spine", parent_id="root")
        
        skeleton = Skeleton(id="skel_1", bones=[root, spine], root_bone_ids=["root"])
        
        error = validate_skeleton(skeleton)
        assert error is None
    
    def test_auto_rig_is_valid(self):
        """Auto-generated rig should be valid."""
        service = AnimationService()
        skeleton = service._create_auto_rig()
        
        error = validate_skeleton(skeleton)
        assert error is None
    
    def test_empty_skeleton_fails(self):
        """Empty skeleton should fail validation."""
        skeleton = Skeleton(id="skel_empty", bones=[], root_bone_ids=["root"])
        
        error = validate_skeleton(skeleton)
        assert error is not None
        assert "no bones" in error.lower()
    
    def test_missing_root_bone_fails(self):
        """Missing root bone should fail."""
        spine = Bone(id="spine", name="Spine")
        skeleton = Skeleton(id="skel_2", bones=[spine], root_bone_ids=["root"])
        
        error = validate_skeleton(skeleton)
        assert error is not None
        assert "root" in error.lower()
    
    def test_invalid_parent_ref_fails(self):
        """Invalid parent reference should fail."""
        spine = Bone(id="spine", name="Spine", parent_id="nonexistent")
        skeleton = Skeleton(id="skel_3", bones=[spine], root_bone_ids=["spine"])
        
        error = validate_skeleton(skeleton)
        assert error is not None
        assert "parent" in error.lower()


class TestIKValidation:
    """Test IK input validation (AV01)."""
    
    def test_valid_ik_input(self):
        """Valid IK input should return None."""
        error = validate_ik_input(
            root_pos=[0.0, 0.0, 0.0],
            target_pos=[1.0, 0.0, 0.0],
            l1=0.5,
            l2=0.5
        )
        assert error is None
    
    def test_invalid_root_pos_length(self):
        """Invalid root_pos should be caught."""
        error = validate_ik_input(
            root_pos=[0.0, 0.0],  # Only 2 elements
            target_pos=[1.0, 0.0, 0.0],
            l1=0.5,
            l2=0.5
        )
        assert error is not None
        assert "root_pos" in error
    
    def test_invalid_target_pos_length(self):
        """Invalid target_pos should be caught."""
        error = validate_ik_input(
            root_pos=[0.0, 0.0, 0.0],
            target_pos=[1.0, 0.0],  # Only 2 elements
            l1=0.5,
            l2=0.5
        )
        assert error is not None
        assert "target_pos" in error
    
    def test_nan_in_root_pos(self):
        """NaN in root_pos should be caught."""
        import math
        error = validate_ik_input(
            root_pos=[0.0, math.nan, 0.0],
            target_pos=[1.0, 0.0, 0.0],
            l1=0.5,
            l2=0.5
        )
        assert error is not None
        assert "NaN" in error or "Inf" in error
    
    def test_nan_in_target_pos(self):
        """NaN in target_pos should be caught."""
        import math
        error = validate_ik_input(
            root_pos=[0.0, 0.0, 0.0],
            target_pos=[1.0, math.nan, 0.0],
            l1=0.5,
            l2=0.5
        )
        assert error is not None
    
    def test_zero_bone_length(self):
        """Zero bone length should be caught."""
        error = validate_ik_input(
            root_pos=[0.0, 0.0, 0.0],
            target_pos=[1.0, 0.0, 0.0],
            l1=0.0,
            l2=0.5
        )
        assert error is not None
        assert "positive" in error.lower() or "length" in error.lower()
    
    def test_negative_bone_length(self):
        """Negative bone length should be caught."""
        error = validate_ik_input(
            root_pos=[0.0, 0.0, 0.0],
            target_pos=[1.0, 0.0, 0.0],
            l1=-0.5,
            l2=0.5
        )
        assert error is not None
    
    def test_ik_solve_with_validation(self):
        """IK solver should work and return valid results."""
        service = AnimationService()
        skeleton = service._create_auto_rig()
        
        # Validate IK inputs
        error = validate_ik_input(
            root_pos=[0.0, 1.0, 0.0],
            target_pos=[0.5, 0.5, 0.0],
            l1=0.5,
            l2=0.5
        )
        assert error is None
        
        # Execute IK solve
        instr = AgentAnimInstruction(
            op_code="IK_SOLVE",
            params={
                "root_pos": [0.0, 1.0, 0.0],
                "target_pos": [0.5, 0.5, 0.0],
                "len_1": 0.5,
                "len_2": 0.5
            },
            target_skeleton_id=skeleton.id
        )
        result = service.execute_instruction(instr)
        assert result is not None
        assert "elbow_pos" in result
        assert "joint_2_angle" in result
