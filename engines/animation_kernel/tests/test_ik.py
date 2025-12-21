"""IK Logic Test."""
import pytest
import math
from engines.animation_kernel.service import AnimationService
from engines.animation_kernel.schemas import AgentAnimInstruction

def test_ik_reach():
    service = AnimationService()
    # Need a skeleton to target
    skel = service.execute_instruction(AgentAnimInstruction(op_code="AUTO_RIG", params={}))
    
    # CASE 1: Reachable Target
    # Root at (0,0,0)
    # L1=1, L2=1. Total Reach=2.
    # Target at (0, 1.5, 0). Should bend elbow.
    res = service.execute_instruction(
        AgentAnimInstruction(
            op_code="IK_SOLVE",
            params={
                "root_pos": [0,0,0],
                "target_pos": [0,1.5,0],
                "len_1": 1.0,
                "len_2": 1.0
            },
            target_skeleton_id=skel.id
        )
    )
    
    assert res is not None
    # With target at 1.5 distance, and arm length 2.0
    # The triangle sides are 1, 1, 1.5
    # Elbow should be pushed out.
    elbow = res["elbow_pos"]
    # Check elbow isn't at zero
    assert abs(elbow[0]) > 0.001 or abs(elbow[2]) > 0.001
    
    # CASE 2: Unreachable Target
    # Target at (0, 3.0, 0).
    res_far = service.execute_instruction(
        AgentAnimInstruction(
            op_code="IK_SOLVE",
            params={
                "root_pos": [0,0,0],
                "target_pos": [0,3.0,0],
                "len_1": 1.0,
                "len_2": 1.0
            },
            target_skeleton_id=skel.id
        )
    )
    # Elbow should be at distance 1.0 towards target.
    # Dir to target is (0,1,0). Elbow should be (0,1,0).
    elbow_far = res_far["elbow_pos"]
    assert abs(elbow_far[0]) < 0.01
    assert abs(elbow_far[1] - 1.0) < 0.01
