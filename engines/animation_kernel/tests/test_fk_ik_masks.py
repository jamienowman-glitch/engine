import math

from engines.animation_kernel.service import MotionLibraryService
from engines.animation_kernel.schemas import MotionClip, Keyframe, Bone, Skeleton, FKIKBoneMask
from engines.animation_kernel.ik_solver import solve_two_bone_ik, vec_len, vec_sub


def test_two_bone_mask_updates_mid_bone_position():
    # Build minimal skeleton root->elbow->hand
    root = Bone(id="root", name="Root", head_pos=[0, 0, 0], tail_pos=[0, 1, 0])
    elbow = Bone(id="elbow", name="Elbow", parent_id="root", head_pos=[0, 1, 0], tail_pos=[0, 1.5, 0])
    hand = Bone(id="hand", name="Hand", parent_id="elbow", head_pos=[0, 1.5, 0], tail_pos=[0, 1.75, 0])
    skel = Skeleton(id="s1", bones=[root, elbow, hand], root_bone_ids=["root"])

    # Create a clip with simple positions (rest pose samples)
    clip = MotionClip(id="c1", name="test", duration=1.0, fps=30.0, bone_tracks={})
    clip.bone_tracks["root"] = [Keyframe(time=0.0, bone_id="root", position=[0.0, 0.0, 0.0])]
    clip.bone_tracks["elbow"] = [Keyframe(time=0.0, bone_id="elbow", position=[0.0, 1.0, 0.0])]
    clip.bone_tracks["hand"] = [Keyframe(time=0.0, bone_id="hand", position=[0.0, 1.5, 0.0])]

    svc = MotionLibraryService()

    # Target offset to the right
    ik_targets = {"hand": [1.2, 1.0, 0.0]}
    masks = [FKIKBoneMask(bone_id="hand", use_ik=True)]

    mixed = svc.apply_fk_ik_mix(clip, masks, ik_targets, skeleton=skel)

    # Find elbow keyframe in mixed clip
    elbow_kfs = mixed.bone_tracks.get("elbow", [])
    assert elbow_kfs, "Elbow keyframe should be present"

    elbow_pos = tuple(elbow_kfs[0].position)

    # Compute expected elbow from analytic two-bone solver
    l1 = vec_len(vec_sub(tuple(elbow.head_pos), tuple(root.head_pos))) if elbow.head_pos else 1.0
    l2 = vec_len(vec_sub(tuple(hand.head_pos), tuple(elbow.head_pos))) if hand.head_pos else 1.0
    expected_elbow, _ = solve_two_bone_ik(tuple(root.head_pos), l1, l2, tuple(ik_targets["hand"]))

    assert vec_len(vec_sub(elbow_pos, expected_elbow)) < 1e-6


def test_mask_false_does_not_modify():
    # Same setup but mask turns off IK
    root = Bone(id="root", name="Root", head_pos=[0, 0, 0], tail_pos=[0, 1, 0])
    elbow = Bone(id="elbow", name="Elbow", parent_id="root", head_pos=[0, 1, 0], tail_pos=[0, 1.5, 0])
    hand = Bone(id="hand", name="Hand", parent_id="elbow", head_pos=[0, 1.5, 0], tail_pos=[0, 1.75, 0])
    skel = Skeleton(id="s2", bones=[root, elbow, hand], root_bone_ids=["root"])

    clip = MotionClip(id="c2", name="test2", duration=1.0, fps=30.0, bone_tracks={})
    clip.bone_tracks["elbow"] = [Keyframe(time=0.0, bone_id="elbow", position=[0.0, 1.0, 0.0])]
    clip.bone_tracks["hand"] = [Keyframe(time=0.0, bone_id="hand", position=[0.0, 1.5, 0.0])]

    svc = MotionLibraryService()
    ik_targets = {"hand": [1.2, 1.0, 0.0]}
    masks = [FKIKBoneMask(bone_id="hand", use_ik=False)]

    mixed = svc.apply_fk_ik_mix(clip, masks, ik_targets, skeleton=skel)

    elbow_kfs = mixed.bone_tracks.get("elbow", [])
    assert elbow_kfs and tuple(elbow_kfs[0].position) == (0.0, 1.0, 0.0)


def test_long_chain_updates_nodes():
    # 4-segment chain: root -> j1 -> j2 -> end
    root = Bone(id="root", name="Root", head_pos=[0, 0, 0], tail_pos=[0, 0.8, 0])
    j1 = Bone(id="j1", name="J1", parent_id="root", head_pos=[0, 0.8, 0], tail_pos=[0, 1.5, 0])
    j2 = Bone(id="j2", name="J2", parent_id="j1", head_pos=[0, 1.5, 0], tail_pos=[0, 2.0, 0])
    end = Bone(id="end", name="End", parent_id="j2", head_pos=[0, 2.0, 0], tail_pos=[0, 2.3, 0])
    skel = Skeleton(id="s3", bones=[root, j1, j2, end], root_bone_ids=["root"])

    clip = MotionClip(id="c3", name="test3", duration=1.0, fps=30.0, bone_tracks={})
    clip.bone_tracks["root"] = [Keyframe(time=0.0, bone_id="root", position=[0.0, 0.0, 0.0])]
    clip.bone_tracks["j1"] = [Keyframe(time=0.0, bone_id="j1", position=[0.0, 0.8, 0.0])]
    clip.bone_tracks["j2"] = [Keyframe(time=0.0, bone_id="j2", position=[0.0, 1.5, 0.0])]
    clip.bone_tracks["end"] = [Keyframe(time=0.0, bone_id="end", position=[0.0, 2.0, 0.0])]

    svc = MotionLibraryService()
    ik_targets = {"end": [1.4, 2.0, 0.0]}
    masks = [FKIKBoneMask(bone_id="end", use_ik=True)]

    mixed = svc.apply_fk_ik_mix(clip, masks, ik_targets, skeleton=skel)

    # Intermediate nodes j1 and j2 should have keyframes at time 0.0
    assert "j1" in mixed.bone_tracks and any(abs(k.time - 0.0) < 1e-6 for k in mixed.bone_tracks["j1"])
    assert "j2" in mixed.bone_tracks and any(abs(k.time - 0.0) < 1e-6 for k in mixed.bone_tracks["j2"])

    # Deterministic: repeated call yields same positions
    mixed2 = svc.apply_fk_ik_mix(clip, masks, ik_targets, skeleton=skel)
    for b in ["j1", "j2"]:
        p1 = next(k.position for k in mixed.bone_tracks[b] if abs(k.time - 0.0) < 1e-6)
        p2 = next(k.position for k in mixed2.bone_tracks[b] if abs(k.time - 0.0) < 1e-6)
        assert tuple(p1) == tuple(p2)


def test_apply_fk_ik_mix_with_no_skeleton_returns_unmodified_clip():
    # ensure service doesn't crash when skeleton is missing and IK mask present
    clip = MotionClip(id="c4", name="nodata", duration=0.5, fps=30.0, bone_tracks={})
    clip.bone_tracks["end"] = [Keyframe(time=0.0, bone_id="end", position=[0.0, 0.0, 0.0])]

    svc = MotionLibraryService()
    masks = [FKIKBoneMask(bone_id="end", use_ik=True)]
    ik_targets = {"end": [1.0, 0.0, 0.0]}

    mixed = svc.apply_fk_ik_mix(clip, masks, ik_targets, skeleton=None)
    # Without skeleton, solver can't run; expect the clip to be returned with same structure
    assert "end" in mixed.bone_tracks
    assert mixed.bone_tracks["end"][0].position == [0.0, 0.0, 0.0]
