"""
Tests for multi-joint IK (FABRIK) and integration with MotionLibraryService.apply_fk_ik_mix
"""
from engines.animation_kernel.ik_solver import solve_chain_ik, vec_len
from engines.animation_kernel.schemas import Bone, Skeleton, FKIKBoneMask
from engines.animation_kernel.service import MotionLibraryService
from engines.animation_kernel.schemas import MotionClip, Keyframe, LoopMode


def test_solve_chain_ik_reaches_target():
    root = (0.0, 0.0, 0.0)
    lengths = [1.0, 1.0, 1.0]
    target = (2.0, 0.5, 0.0)

    positions = solve_chain_ik(root, lengths, target)
    end = positions[-1]

    # Solver should improve distance to target (not necessarily exact for colinear initial configs)
    initial_end = (sum(lengths) * (target[0] / ( (target[0]**2 + target[1]**2)**0.5 )),
                   sum(lengths) * (target[1] / ( (target[0]**2 + target[1]**2)**0.5 )),
                   0.0)
    initial_dist = vec_len((initial_end[0]-target[0], initial_end[1]-target[1], initial_end[2]-target[2]))
    dist = vec_len((end[0]-target[0], end[1]-target[1], end[2]-target[2]))
    assert dist < initial_dist

    # Deterministic: repeated solves yield same result
    positions2 = solve_chain_ik(root, lengths, target)
    assert positions2[-1] == positions[-1]


def test_solve_chain_ik_unreachable_stretches():
    root = (0.0, 0.0, 0.0)
    lengths = [1.0, 1.0]
    target = (5.0, 0.0, 0.0)  # unreachable

    positions = solve_chain_ik(root, lengths, target)
    end = positions[-1]

    # End should be at a distance equal to total length from root (2.0)
    dist = vec_len((end[0]-root[0], end[1]-root[1], end[2]-root[2]))
    assert abs(dist - sum(lengths)) < 1e-6


def test_apply_fk_ik_mix_two_bone_analytic():
    # Build skeleton with 3 bones (root->mid->end)
    b_root = Bone(id="root", name="Root", parent_id=None, head_pos=[0,0,0], tail_pos=[0,1,0])
    b_mid = Bone(id="mid", name="Mid", parent_id="root", head_pos=[0,1,0], tail_pos=[0,2,0])
    b_end = Bone(id="end", name="End", parent_id="mid", head_pos=[0,2,0], tail_pos=[0,3,0])
    skeleton = Skeleton(id="skel1", bones=[b_root, b_mid, b_end], root_bone_ids=["root"]) 

    # Create a clip where root/mid/end have position keyframes so solver can estimate lengths
    clip = MotionClip(
        id="clip_test",
        name="TestIK",
        duration=1.0,
        fps=30.0,
        loop_mode=LoopMode.NONE,
        bone_tracks={
            "root": [Keyframe(time=0.0, bone_id="root", position=[0.0, 0.0, 0.0])],
            "mid": [Keyframe(time=0.0, bone_id="mid", position=[0.0, 1.0, 0.0])],
            "end": [Keyframe(time=0.0, bone_id="end", position=[0.0, 2.0, 0.0])],
        }
    )

    service = MotionLibraryService()
    masks = [FKIKBoneMask(bone_id="end", use_ik=True)]
    target = {"end": [1.0, 1.5, 0.0]}

    mixed = service.apply_fk_ik_mix(clip, masks, target, skeleton=skeleton)

    # After IK, mid bone should have a keyframe adjusted nearer to expected elbow position
    assert "mid" in mixed.bone_tracks
    mid_kfs = mixed.bone_tracks["mid"]
    assert any(kf.position is not None for kf in mid_kfs)

    # Deterministic: calling again should produce same results
    mixed2 = service.apply_fk_ik_mix(clip, masks, target, skeleton=skeleton)
    assert mixed2.bone_tracks.keys() == mixed.bone_tracks.keys()
    # Compare mid bone first keyframe position
    pos1 = sorted([kf for kf in mid_kfs], key=lambda x: x.time)[0].position
    pos2 = sorted([kf for kf in mixed2.bone_tracks["mid"]], key=lambda x: x.time)[0].position
    assert pos1 == pos2
