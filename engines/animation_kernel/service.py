"""Animation Service for Phase 3-4 (AV01-AV04)."""
import uuid
import math
from typing import Dict, Optional, List

from engines.animation_kernel.schemas import (
    AgentAnimInstruction, Skeleton, Bone, AnimationClip, AnimOpCode,
    MotionLibrary, MotionClip, Keyframe, LoopMode, FKIKBoneMask, AnimationBlend,
    ExportMetadata
)

class AnimationService:
    def __init__(self):
        self._skeletons: Dict[str, Skeleton] = {} # id -> Skeleton
        self._clips: Dict[str, AnimationClip] = {} # id -> Clip

    def execute_instruction(self, instruction: AgentAnimInstruction) -> Optional[object]:
        """
        Executes an animation instruction.
        """
        op = instruction.op_code.upper()
        params = instruction.params
        target_id = instruction.target_skeleton_id
        
        if op == "AUTO_RIG":
            # For V1, we just create a "StickMan" skeleton regardless of mesh input
            # In V2, we would analyze the mesh bounds.
            return self._create_auto_rig()
            
        if target_id and target_id in self._skeletons:
            skeleton = self._skeletons[target_id]
            
            if op == "PLAY_ANIM":
                # Returns a "Pose" (Dict of Transforms) at time t
                clip_name = params.get("clip_name")
                time = params.get("time", 0.0)
                # Find clip (mock lookup)
                # In real app, clips are in a library.
                # Let's mock a walk cycle if requested
                if clip_name == "WALK":
                    return self._evaluate_walk_cycle(skeleton, time)
                return {}
            
            elif op == "IK_SOLVE":
                # params: root_pos (vec3), target_pos (vec3), l1, l2
                # Returns: {joint_1_rot: quat, joint_2_rot: float}
                from engines.animation_kernel.ik_solver import solve_two_bone_ik
                
                start = params.get("root_pos")
                target = params.get("target_pos")
                l1 = params.get("len_1", 1.0)
                l2 = params.get("len_2", 1.0)
                
                elbow_pos, j2_angle = solve_two_bone_ik(
                    root_pos=tuple(start), 
                    joint_len_1=l1, 
                    joint_len_2=l2, 
                    target_pos=tuple(target)
                )
                # For showcase visualization, we might just return endpoint positions or simple rotations.
                # Our Showcase script will use this data to set Three.js bone properties.
                return {
                    "elbow_pos": elbow_pos,
                    "joint_2_angle": j2_angle
                }

        return None

    def _create_auto_rig(self) -> Skeleton:
        """Creates a standard humanoid hierarchy with Legs."""
        skel_id = str(uuid.uuid4())
        
        # Standard Humanoid Logic (Y-Up, 1 unit = 1 meter approx)
        # Hips at 0.9m
        root_y = 0.9
        
        # Central Line
        root = Bone(id="root", name="Root", head_pos=[0, root_y, 0], tail_pos=[0, root_y+0.1, 0])
        spine = Bone(id="spine", name="Spine", parent_id="root", head_pos=[0, root_y, 0], tail_pos=[0, 1.4, 0]) # Torso up to neck
        head = Bone(id="head", name="Head", parent_id="spine", head_pos=[0, 1.4, 0], tail_pos=[0, 1.75, 0])
        
        # Arms (T-Pose) - attached at Spine top (Neck/Shoulder junction)
        shoulder_y = 1.35
        arm_span = 0.2
        
        shoulder_l = Bone(id="shoulder_l", name="Shoulder_L", parent_id="spine", head_pos=[0, shoulder_y, 0], tail_pos=[-arm_span, shoulder_y, 0])
        arm_l = Bone(id="arm_l", name="Arm_L", parent_id="shoulder_l", head_pos=[-arm_span, shoulder_y, 0], tail_pos=[-arm_span-0.3, shoulder_y, 0])
        forearm_l = Bone(id="forearm_l", name="Forearm_L", parent_id="arm_l", head_pos=[-arm_span-0.3, shoulder_y, 0], tail_pos=[-arm_span-0.6, shoulder_y, 0])
        
        shoulder_r = Bone(id="shoulder_r", name="Shoulder_R", parent_id="spine", head_pos=[0, shoulder_y, 0], tail_pos=[arm_span, shoulder_y, 0])
        arm_r = Bone(id="arm_r", name="Arm_R", parent_id="shoulder_r", head_pos=[arm_span, shoulder_y, 0], tail_pos=[arm_span+0.3, shoulder_y, 0])
        forearm_r = Bone(id="forearm_r", name="Forearm_R", parent_id="arm_r", head_pos=[arm_span+0.3, shoulder_y, 0], tail_pos=[arm_span+0.6, shoulder_y, 0])
        
        # Legs - attached at Root (Hips)
        hip_span = 0.1
        knee_y = 0.5
        foot_y = 0.05
        
        thigh_l = Bone(id="thigh_l", name="Thigh_L", parent_id="root", head_pos=[-hip_span, root_y, 0], tail_pos=[-hip_span, knee_y, 0])
        calf_l = Bone(id="calf_l", name="Calf_L", parent_id="thigh_l", head_pos=[-hip_span, knee_y, 0], tail_pos=[-hip_span, foot_y, 0])
        foot_l = Bone(id="foot_l", name="Foot_L", parent_id="calf_l", head_pos=[-hip_span, foot_y, 0], tail_pos=[-hip_span, 0, 0.15])
        
        thigh_r = Bone(id="thigh_r", name="Thigh_R", parent_id="root", head_pos=[hip_span, root_y, 0], tail_pos=[hip_span, knee_y, 0])
        calf_r = Bone(id="calf_r", name="Calf_R", parent_id="thigh_r", head_pos=[hip_span, knee_y, 0], tail_pos=[hip_span, foot_y, 0])
        foot_r = Bone(id="foot_r", name="Foot_R", parent_id="calf_r", head_pos=[hip_span, foot_y, 0], tail_pos=[hip_span, 0, 0.15])
        
        bones = [
            root, spine, head, 
            shoulder_l, arm_l, forearm_l, 
            shoulder_r, arm_r, forearm_r,
            thigh_l, calf_l, foot_l,
            thigh_r, calf_r, foot_r
        ]
        self._skeletons[skel_id] = Skeleton(id=skel_id, bones=bones, root_bone_ids=["root"])
        return self._skeletons[skel_id]

    def _evaluate_walk_cycle(self, skeleton: Skeleton, time: float) -> Dict[str, List[float]]:
        """
        Procedural Walk Cycle Evaluator.
        Returns: {bone_id: [qx, qy, qz, qw]} (Local Rotation)
        """
        pose = {}
        # 1 Hz cycle
        phase = (time % 1.0) * 2 * math.pi
        
        # Head bobs
        # Spine rotates slightly
        # For this test, just rotate root
        
        # Simple Sine rotation around Y
        angle = math.sin(phase) * 0.1 # radians
        # Axis Angle Y -> Quat
        # q = [0, sin(a/2), 0, cos(a/2)]
        qx = 0.0
        qy = math.sin(angle/2)
        qz = 0.0
        qw = math.cos(angle/2)
        
        pose["root"] = [qx, qy, qz, qw]
        return pose

# ===== PHASE AV01: IK Input Validation =====

def validate_ik_input(
    root_pos: List[float],
    target_pos: List[float],
    l1: float,
    l2: float
) -> Optional[str]:
    """
    Validate IK solver input parameters.
    
    Args:
        root_pos: [x, y, z] root position
        target_pos: [x, y, z] target position
        l1: Upper limb length
        l2: Lower limb length
    
    Returns:
        Error message if invalid, None if valid
    """
    import math
    
    # Check input types and lengths
    if not isinstance(root_pos, (list, tuple)) or len(root_pos) != 3:
        return "root_pos must be [x, y, z]"
    if not isinstance(target_pos, (list, tuple)) or len(target_pos) != 3:
        return "target_pos must be [x, y, z]"
    
    # Check for NaN/Inf
    for coord in root_pos:
        if math.isnan(float(coord)) or math.isinf(float(coord)):
            return f"root_pos contains NaN/Inf: {root_pos}"
    for coord in target_pos:
        if math.isnan(float(coord)) or math.isinf(float(coord)):
            return f"target_pos contains NaN/Inf: {target_pos}"
    
    # Check bone lengths
    if l1 <= 0 or l2 <= 0:
        return f"Bone lengths must be positive: l1={l1}, l2={l2}"
    if math.isnan(l1) or math.isinf(l1) or math.isnan(l2) or math.isinf(l2):
        return f"Bone lengths contain NaN/Inf: l1={l1}, l2={l2}"
    
    return None


def validate_skeleton(skeleton: Skeleton) -> Optional[str]:
    """
    Validate a skeleton structure.
    
    Args:
        skeleton: Skeleton to validate
    
    Returns:
        Error message if invalid, None if valid
    """
    import math
    
    if not skeleton.bones:
        return "Skeleton has no bones"
    
    bone_ids = {bone.id for bone in skeleton.bones}
    
    # Check root bones exist
    if not skeleton.root_bone_ids:
        return "Skeleton has no root bones"
    
    for root_id in skeleton.root_bone_ids:
        if root_id not in bone_ids:
            return f"Root bone '{root_id}' not found in skeleton"
    
    # Check parent references
    for bone in skeleton.bones:
        if bone.parent_id and bone.parent_id not in bone_ids:
            return f"Bone '{bone.id}' references non-existent parent '{bone.parent_id}'"
    
    # Check for NaN/invalid positions
    for bone in skeleton.bones:
        for coord in bone.head_pos + bone.tail_pos:
            if math.isnan(float(coord)) or math.isinf(float(coord)):
                return f"Bone '{bone.id}' has NaN/Inf position: head={bone.head_pos}, tail={bone.tail_pos}"
    
    return None


# ===== PHASE AV04: Motion Library & Blending =====

class MotionLibraryService:
    """Service for managing and playing motion clips."""
    
    def __init__(self):
        self._libraries: Dict[str, MotionLibrary] = {}
        self._clips: Dict[str, MotionClip] = {}
    
    def create_library(self, name: str) -> MotionLibrary:
        """Create a new motion library."""
        lib = MotionLibrary(id=str(uuid.uuid4()), name=name)
        self._libraries[lib.id] = lib
        return lib
    
    def add_clip_to_library(self, library_id: str, clip: MotionClip) -> Optional[MotionClip]:
        """Add a motion clip to a library."""
        if library_id not in self._libraries:
            return None
        lib = self._libraries[library_id]
        lib.clips[clip.id] = clip
        self._clips[clip.id] = clip
        return clip
    
    def get_clip(self, clip_id: str) -> Optional[MotionClip]:
        """Retrieve a motion clip by ID."""
        return self._clips.get(clip_id)
    
    def playback_at_time(self, clip: MotionClip, time: float, skeleton: Optional[Skeleton] = None) -> Dict[str, List[float]]:
        """
        Evaluate animation at specific time.
        
        Args:
            clip: MotionClip to play
            time: Time in seconds
            skeleton: Optional skeleton for validation
        
        Returns:
            Dict mapping bone_id to [qx, qy, qz, qw] quaternion
        """
        # Handle looping
        if clip.loop_mode == LoopMode.NONE:
            # Clamp to duration
            eval_time = min(time, clip.duration)
        elif clip.loop_mode == LoopMode.LOOP:
            # Standard loop
            eval_time = time % clip.duration if clip.duration > 0 else 0.0
        elif clip.loop_mode == LoopMode.PING_PONG:
            # Ping pong - go forward then backward
            cycle_duration = clip.duration * 2 if clip.duration > 0 else 1.0
            t_in_cycle = time % cycle_duration
            if t_in_cycle > clip.duration:
                eval_time = clip.duration - (t_in_cycle - clip.duration)
            else:
                eval_time = t_in_cycle
        else:
            eval_time = time % clip.duration if clip.duration > 0 else 0.0
        
        # Interpolate keyframes for each bone
        pose = {}
        for bone_id, keyframes in clip.bone_tracks.items():
            quat = self._interpolate_bone_at_time(keyframes, eval_time)
            if quat:
                pose[bone_id] = quat
        
        return pose
    
    def _interpolate_bone_at_time(self, keyframes: List[Keyframe], time: float) -> Optional[List[float]]:
        """
        Interpolate rotation at time t.
        
        Args:
            keyframes: List of keyframes for a bone
            time: Time to evaluate at
        
        Returns:
            [qx, qy, qz, qw] quaternion or None
        """
        if not keyframes:
            return None
        
        # Sort keyframes by time
        sorted_kf = sorted(keyframes, key=lambda k: k.time)
        
        # Find surrounding keyframes
        before = None
        after = None
        
        for kf in sorted_kf:
            if kf.time <= time:
                before = kf
            if kf.time >= time and after is None:
                after = kf
        
        # If exactly on a keyframe
        if before and before.time == time and before.rotation:
            return before.rotation
        if after and after.time == time and after.rotation:
            return after.rotation
        
        # Interpolate between before and after
        if before and after and before.rotation and after.rotation:
            # Linear interpolation in quaternion space (slerp would be better but lerp works for many cases)
            t_ratio = (time - before.time) / (after.time - before.time) if after.time != before.time else 0.0
            t_ratio = max(0.0, min(1.0, t_ratio))
            
            # Simple lerp (not proper slerp)
            result = []
            for i in range(4):
                val = before.rotation[i] * (1 - t_ratio) + after.rotation[i] * t_ratio
                result.append(val)
            return result
        
        # If only before exists, return it
        if before and before.rotation:
            return before.rotation
        
        # If only after exists, return it
        if after and after.rotation:
            return after.rotation
        
        return None
    
    def blend_clips(self, clip1: MotionClip, clip2: MotionClip, blend_time: float, skeleton: Optional[Skeleton] = None) -> MotionClip:
        """
        Blend two animation clips with crossfade.
        
        Args:
            clip1: Starting clip
            clip2: Ending clip
            blend_time: Duration of blend transition
            skeleton: Optional skeleton for validation
        
        Returns:
            Blended MotionClip
        """
        blended_id = str(uuid.uuid4())
        blended_name = f"blend_{clip1.name}_to_{clip2.name}"
        blended_duration = clip1.duration + blend_time
        
        blended_tracks = {}
        
        # Collect all bone IDs from both clips
        all_bones = set(clip1.bone_tracks.keys()) | set(clip2.bone_tracks.keys())
        
        for bone_id in all_bones:
            blended_tracks[bone_id] = []
            
            # Sample from clip1 up to duration
            if bone_id in clip1.bone_tracks:
                blended_tracks[bone_id].extend(clip1.bone_tracks[bone_id])
            
            # Add transition keyframes at blend boundary
            # At clip1.duration, fade out clip1, fade in clip2
            blend_start_time = clip1.duration
            blend_end_time = blend_start_time + blend_time
            
            # For simplicity, we just append clip2's keyframes shifted in time
            if bone_id in clip2.bone_tracks:
                for kf in clip2.bone_tracks[bone_id]:
                    shifted_kf = Keyframe(
                        time=blend_start_time + kf.time,
                        bone_id=kf.bone_id,
                        position=kf.position,
                        rotation=kf.rotation,
                        scale=kf.scale
                    )
                    blended_tracks[bone_id].append(shifted_kf)
        
        blended_clip = MotionClip(
            id=blended_id,
            name=blended_name,
            duration=blended_duration,
            fps=clip1.fps,
            loop_mode=LoopMode.NONE,
            bone_tracks=blended_tracks
        )
        
        return blended_clip
    
    def apply_fk_ik_mix(self, clip: MotionClip, fk_ik_masks: List[FKIKBoneMask], ik_targets: Dict[str, List[float]], skeleton: Optional[Skeleton] = None) -> MotionClip:
        """
        Apply FK/IK mixing to a clip. Uses analytic two-bone solver when chain length==2 or FABRIK for longer chains if skeleton is provided.
        
        Args:
            clip: Motion clip to modify
            fk_ik_masks: List of bones to apply IK to
            ik_targets: Dict of bone_id -> target position [x, y, z]
            skeleton: Optional Skeleton to discover joint chains and bone order
        
        Returns:
            Modified MotionClip
        """
        from engines.animation_kernel.ik_solver import solve_two_bone_ik, solve_chain_ik, vec_len, vec_sub

        mixed_id = str(uuid.uuid4())
        mixed_tracks = {}
        
        # Copy all bone tracks
        for bone_id, keyframes in clip.bone_tracks.items():
            mixed_tracks[bone_id] = [Keyframe(
                time=kf.time,
                bone_id=kf.bone_id,
                position=kf.position,
                rotation=kf.rotation,
                scale=kf.scale
            ) for kf in keyframes]
        
        # Helper: find chain from root to a bone using skeleton
        def _find_chain(target_bone_id: str) -> List[str]:
            if skeleton is None:
                return []
            # Build parent map
            parent_map = {b.id: b.parent_id for b in skeleton.bones}
            chain = []
            curr = target_bone_id
            while curr:
                chain.append(curr)
                curr = parent_map.get(curr)
            chain.reverse()  # root -> ... -> target
            return chain

        # Apply IK corrections to specified bones
        for mask in fk_ik_masks:
            if not mask.use_ik or mask.bone_id not in ik_targets:
                continue
            target = ik_targets[mask.bone_id]
            chain = _find_chain(mask.bone_id)

            # If chain length 3 nodes => 2 segments => two-bone solver
            if len(chain) == 3:
                # bone ids: [root, mid, end]
                root_id, mid_id, end_id = chain

                # Use average segment lengths from animation keyframes if possible, otherwise fallback
                # Compute segment lengths from first keyframe positions if available
                def _estimate_lengths(root_id, mid_id, end_id):
                    # Try to get positions from existing keyframes; else default to 1.0
                    l1 = 1.0
                    l2 = 1.0
                    # If positions are present in keyframes (position fields), compute dist
                    rpos = None
                    mpos = None
                    epos = None
                    # Look for first position sample in tracks
                    if root_id in mixed_tracks and mixed_tracks[root_id]:
                        if mixed_tracks[root_id][0].position:
                            rpos = tuple(mixed_tracks[root_id][0].position)
                    if mid_id in mixed_tracks and mixed_tracks[mid_id]:
                        if mixed_tracks[mid_id][0].position:
                            mpos = tuple(mixed_tracks[mid_id][0].position)
                    if end_id in mixed_tracks and mixed_tracks[end_id]:
                        if mixed_tracks[end_id][0].position:
                            epos = tuple(mixed_tracks[end_id][0].position)
                    if rpos and mpos:
                        l1 = vec_len(vec_sub(mpos, rpos))
                    if mpos and epos:
                        l2 = vec_len(vec_sub(epos, mpos))
                    return l1, l2

                l1, l2 = _estimate_lengths(root_id, mid_id, end_id)

                # For each keyframe time, solve IK and insert/update mid bone positions
                times = set()
                for kf in mixed_tracks.get(end_id, []):
                    times.add(kf.time)
                for t in sorted(times):
                    # Solve IK for this instant
                    # Use simple two-bone analytic solver
                    # Need root position and end target
                    root_pos = None
                    # Try to find root position from tracks
                    if root_id in mixed_tracks and mixed_tracks[root_id]:
                        # Use first sample position if present
                        if mixed_tracks[root_id][0].position:
                            root_pos = tuple(mixed_tracks[root_id][0].position)
                    if root_pos is None:
                        # fallback root at origin
                        root_pos = (0.0, 0.0, 0.0)

                    elbow_pos, joint2_angle = solve_two_bone_ik(root_pos, l1, l2, tuple(target))

                    # Update/append mid bone keyframe with elbow position
                    mid_kfs = mixed_tracks.setdefault(mid_id, [])
                    # Replace or insert keyframe at time t
                    replaced = False
                    for kf in mid_kfs:
                        if abs(kf.time - t) < 1e-6:
                            kf.position = list(elbow_pos)
                            replaced = True
                            break
                    if not replaced:
                        mid_kfs.append(Keyframe(time=t, bone_id=mid_id, position=list(elbow_pos)))

            elif len(chain) > 3:
                # Use FABRIK solver for longer chains
                # Build joint lengths list
                joint_lengths = []
                for i in range(len(chain)-1):
                    a = chain[i]
                    b = chain[i+1]
                    # Estimate length between a and b from first sample positions
                    l = 1.0
                    if a in mixed_tracks and mixed_tracks[a] and mixed_tracks[a][0].position and b in mixed_tracks and mixed_tracks[b] and mixed_tracks[b][0].position:
                        pa = tuple(mixed_tracks[a][0].position)
                        pb = tuple(mixed_tracks[b][0].position)
                        l = vec_len(vec_sub(pb, pa))
                    joint_lengths.append(l)

                # Solve single pass for target and update mid nodes with positions
                root_id = chain[0]
                root_pos = (0.0, 0.0, 0.0)
                if root_id in mixed_tracks and mixed_tracks[root_id] and mixed_tracks[root_id][0].position:
                    root_pos = tuple(mixed_tracks[root_id][0].position)

                positions = solve_chain_ik(root_pos, joint_lengths, tuple(target))

                # positions include root .. end
                for idx, node_id in enumerate(chain[1:]):
                    pos = positions[idx+1]
                    kfs = mixed_tracks.setdefault(node_id, [])
                    # Insert at time 0 only (simplified). Could sample per keyframe time for full fidelity.
                    inserted = False
                    for kf in kfs:
                        if abs(kf.time - 0.0) < 1e-6:
                            kf.position = list(pos)
                            inserted = True
                            break
                    if not inserted:
                        kfs.append(Keyframe(time=0.0, bone_id=node_id, position=list(pos)))

            else:
                # Chain too short or skeleton not provided; can't solve
                pass

        mixed_clip = MotionClip(
            id=mixed_id,
            name=f"{clip.name}_fkik_mixed",
            duration=clip.duration,
            fps=clip.fps,
            loop_mode=clip.loop_mode,
            bone_tracks=mixed_tracks
        )
        
        return mixed_clip


def create_export_metadata(
    avatar_id: str,
    format: str = "gltf",
    has_rig: bool = True,
    has_meshes: bool = True,
    has_morphs: bool = False,
    has_materials: bool = False,
    animation_clip_ids: List[str] = None
) -> ExportMetadata:
    """
    Create metadata for avatar export.
    
    Args:
        avatar_id: ID of avatar being exported
        format: Export format (gltf, usd, etc.)
        has_rig: Whether to include rigging
        has_meshes: Whether to include meshes
        has_morphs: Whether to include morph targets
        has_materials: Whether to include materials
        animation_clip_ids: List of animation clip IDs to include
    
    Returns:
        ExportMetadata
    """
    return ExportMetadata(
        avatar_id=avatar_id,
        format=format,
        has_rig=has_rig,
        has_meshes=has_meshes,
        has_morphs=has_morphs,
        has_materials=has_materials,
        has_animations=animation_clip_ids or []
    )