"""
Inverse Kinematics Solver (Level B).
Implements analytic Two-Bone IK for robotic limbs.
"""
import math
from typing import Dict, Optional, Tuple, List

# Re-use our geometry types. Ideally these should be in a shared math lib
# but for now we interpret simple dicts/tuples to avoid heavy dependencies in the kernel core.
Vector3 = Tuple[float, float, float]
Quaternion = Tuple[float, float, float, float]

def vec_sub(a: Vector3, b: Vector3) -> Vector3:
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])

def vec_add(a: Vector3, b: Vector3) -> Vector3:
    return (a[0]+b[0], a[1]+b[1], a[2]+b[2])

def vec_mul(a: Vector3, s: float) -> Vector3:
    return (a[0]*s, a[1]*s, a[2]*s)

def vec_dot(a: Vector3, b: Vector3) -> float:
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]

def vec_cross(a: Vector3, b: Vector3) -> Vector3:
    return (
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0]
    )

def vec_len(v: Vector3) -> float:
    return math.sqrt(vec_dot(v, v))

def vec_norm(v: Vector3) -> Vector3:
    l = vec_len(v)
    if l < 1e-6: return (0,0,0)
    return vec_mul(v, 1.0/l)

def quat_from_axis_angle(axis: Vector3, angle: float) -> Quaternion:
    """Standard Quat construction."""
    half = angle * 0.5
    s = math.sin(half)
    return (axis[0]*s, axis[1]*s, axis[2]*s, math.cos(half))

def quat_mul(q1: Quaternion, q2: Quaternion) -> Quaternion:
    """Hamilton Product."""
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return (
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2
    )

def solve_two_bone_ik(
    root_pos: Vector3,
    joint_len_1: float,
    joint_len_2: float,
    target_pos: Vector3,
    pole_vector: Vector3 = (0, 1, 0) # Direction elbow should point
) -> Tuple[Quaternion, float]:
    """
    Calculates the rotations for a 2-bone chain (e.g. Arm).
    Returns:
        tuple: (RootRotation (Quaternion), Joint2Angle (Radians))
    
    Using Law of Cosines:
    c^2 = a^2 + b^2 - 2ab cos(C)
    """
    
    # Vector from Root to Target
    to_target = vec_sub(target_pos, root_pos)
    dist = vec_len(to_target)
    
    # Clamp distance (can't reach further than straight arm)
    total_len = joint_len_1 + joint_len_2
    dist = min(dist, total_len - 0.001) # epsilon prevents div/0
    dist = max(dist, 0.001)
    
    # 1. Calculate Knee/Elbow Angle (Joint 2)
    # Cosine Rule: dist^2 = l1^2 + l2^2 - 2*l1*l2*cos(180 - angle)
    # interior angle C
    # c^2 = a^2 + b^2 - 2ab cos C
    # dist^2 = l1^2 + l2^2 - 2*l1*l2 * cos(interior_angle)
    # cos(interior) = (l1^2 + l2^2 - dist^2) / (2*l1*l2)
    
    cos_angle_inner = (joint_len_1**2 + joint_len_2**2 - dist**2) / (2 * joint_len_1 * joint_len_2)
    # Clamp for floating point errors
    cos_angle_inner = max(-1.0, min(1.0, cos_angle_inner))
    angle_inner = math.acos(cos_angle_inner)
    
    # The actual joint rotation is typically the deviation from straight.
    # If standard pose is T-pose (180 deg), then rotation is (180 - interior)
    # But usually bones are parented such that 0 rot = straight.
    # Let's assume 0 rot = straight line.
    # Then we bend by (180 - interior)
    joint_2_angle = math.pi - angle_inner
    
    # 2. Calculate Root Rotation (Joint 1)
    # This involves aligning the limb plane with the standard pole vector
    
    # Angle between Root->Target line and Root->Elbow
    # a^2 = b^2 + c^2 - 2bc cos A
    # l2^2 = l1^2 + dist^2 - 2*l1*dist * cos(alpha)
    cos_alpha = (joint_len_1**2 + dist**2 - joint_len_2**2) / (2 * joint_len_1 * dist)
    cos_alpha = max(-1.0, min(1.0, cos_alpha))
    alpha = math.acos(cos_alpha)
    
    # Rotation 1: Bend towards target in the plane
    # Basic direction to target
    dir_to_target = vec_norm(to_target)
    
    # We need a formulation for the full quaternion of the root.
    # Simplified approach for showcase:
    # 1. LookAt(target)
    # 2. Rotate by 'alpha' away from LookAt, based on plane defined by Pole Vector.
    
    # Let's return the simpler components for the Agent to use in standard transforms if possible.
    # But for a robust solver we return the Quat.
    
    # Vector perpendicular to limb plane (Normal)
    # Normal = dir_to_target x pole_vector (if pole is generic up)
    # Or define plane by Root, Target, Pole.
    
    plane_normal = vec_cross(dir_to_target, pole_vector)
    if vec_len(plane_normal) < 0.001:
        plane_normal = (1, 0, 0) # arbitrary
    plane_normal = vec_norm(plane_normal)
    
    # Basic orientation pointing to target
    # (Assuming forward is Z+ for bones... standard rigging conventions vary wildly.
    #  Let's assume Y+ is bone Axis like Blender/Maya standard usually is Y or X.
    #  We will stick to Y+ is "along the bone")
    
    # Rotate Y-axis (0,1,0) to coincide with dir_to_target
    # But wait, we must actually point to the *Elbow*, not the Target.
    # The Elbow is rotated by 'alpha' from the Target vector.
    
    # Rotate dir_to_target by alpha around plane_normal
    rot_alpha = quat_from_axis_angle(plane_normal, alpha)
    
    # Now rotate standard vector (0,1,0) to target?
    # This vector math can get hairy without a Matrix lib.
    # For this showcase, we will simplify:
    # Return just the angles required for a graphical wrapper to construct.
    
    # ACTUALLY: Let's cheat slightly for robustness.
    # We return the **Elbow Position**. 
    # The caller can then simply "LookAt" Elbow from Shoulder, and "LookAt" Target from Elbow.
    # This is much safer than quaternion hell in raw python.
    
    # Elbow position is:
    # Root + (Rotation(alpha) * dir_to_target * l1)
    
    # Rotate vector 'dir_to_target' by 'alpha' around 'plane_normal'
    # Rodrigues rotation formula
    # v_rot = v cos a + (k x v) sin a + k (k . v) (1 - cos a)
    # k = plane_normal, v = dir_to_target
    
    k = plane_normal
    v = dir_to_target
    theta = alpha
    
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    k_cross_v = vec_cross(k, v)
    k_dot_v = vec_dot(k, v) # Should be 0 since k is cross product of v and something
    
    # v_rot = v * cos_t + k_cross_v * sin_t
    v_rot = vec_add(vec_mul(v, cos_t), vec_mul(k_cross_v, sin_t))
    
    elbow_pos = vec_add(root_pos, vec_mul(v_rot, joint_len_1))
    
    # But wait, we need Rotations for the Bone Animation protocol.
    # The protocol expects a Keyframe (Transform).
    # If we return positions, we need to convert to rotation.
    
    # Let's return the computed positions of the joints.
    # The AnimationService wrapper will deal with constructing LookAt matrices/quats if needed,
    # or we just update the bone TIP position if our engine supports FK/IK hybrid.
    # Our engine is simple.
    
    return elbow_pos, joint_2_angle


def _quat_conjugate(q: Quaternion) -> Quaternion:
    x, y, z, w = q
    return (-x, -y, -z, w)


def _quat_rotate_vector(q: Quaternion, v: Vector3) -> Vector3:
    # Rotate vector v by quaternion q: q * v * q_conj (treat v as quaternion [v,0])
    x, y, z, w = q
    # q * v
    vx =  w * v[0] + y * v[2] - z * v[1]
    vy =  w * v[1] + z * v[0] - x * v[2]
    vz =  w * v[2] + x * v[1] - y * v[0]
    vw = -x * v[0] - y * v[1] - z * v[2]
    # (q*v) * q_conj
    cx = vw * (-x) + vx * w + vy * (-z) - vz * (-y)
    cy = vw * (-y) + vy * w + vz * (-x) - vx * (-z)
    cz = vw * (-z) + vz * w + vx * (-y) - vy * (-x)
    return (cx, cy, cz)


def solve_chain_ik(
    root_pos: Vector3,
    joint_lengths: List[float],
    target_pos: Vector3,
    max_iters: int = 40,
    tolerance: float = 1e-4
) -> List[Vector3]:
    """
    CCD-based IK solver for n-joint chain.

    Args:
        root_pos: position of the root (first joint)
        joint_lengths: list of segment lengths [l1, l2, ...]
        target_pos: desired end effector position
        max_iters: maximum solver iterations
        tolerance: distance tolerance to target

    Returns:
        List of joint world positions (including root_pos and end effector)
    """
    n = len(joint_lengths) + 1
    # Initialize positions along straight line to target
    positions: List[Vector3] = [root_pos]
    dir_rt = vec_norm(vec_sub(target_pos, root_pos))
    if vec_len(dir_rt) < 1e-6:
        dir_rt = (1.0, 0.0, 0.0)
    pos = root_pos
    for l in joint_lengths:
        pos = vec_add(pos, vec_mul(dir_rt, l))
        positions.append(pos)

    # Detect near-colinear initial configuration and apply a tiny deterministic
    # perpendicular offset to break perfect symmetry which can cause FABRIK to
    # stagnate in certain configurations (e.g., perfectly stretched along target).
    # This offset is small, deterministic, and ensures solver makes progress.
    eps = 1e-6
    # Pick an arbitrary non-parallel axis to compute a perpendicular
    up = (0.0, 1.0, 0.0)
    perp = vec_cross(dir_rt, up)
    if vec_len(perp) < 1e-8:
        perp = (1.0, 0.0, 0.0)
    perp = vec_norm(perp)
    # Apply scaled offsets to internal joints
    for i in range(1, len(positions)-1):
        scale = eps * (i / float(len(positions)))
        positions[i] = vec_add(positions[i], vec_mul(perp, scale))

    total_len = sum(joint_lengths)
    if vec_len(vec_sub(target_pos, root_pos)) > total_len:
        # unreachable -> stretch
        dir_to_target = vec_norm(vec_sub(target_pos, root_pos))
        positions = [root_pos]
        pos = root_pos
        for l in joint_lengths:
            pos = vec_add(pos, vec_mul(dir_to_target, l))
            positions.append(pos)
        return positions

    # Iterative FABRIK-like (lambda) solver
    for it in range(max_iters):
        # Forward reaching
        positions[-1] = target_pos
        for i in range(n-2, -1, -1):
            r = vec_len(vec_sub(positions[i+1], positions[i]))
            if r < 1e-9:
                continue
            lam = joint_lengths[i] / r
            positions[i] = (
                positions[i+1][0] + (positions[i][0] - positions[i+1][0]) * lam,
                positions[i+1][1] + (positions[i][1] - positions[i+1][1]) * lam,
                positions[i+1][2] + (positions[i][2] - positions[i+1][2]) * lam,
            )

        # Backward reaching
        positions[0] = root_pos
        for i in range(0, n-1):
            r = vec_len(vec_sub(positions[i+1], positions[i]))
            if r < 1e-9:
                continue
            lam = joint_lengths[i] / r
            positions[i+1] = (
                positions[i][0] + (positions[i+1][0] - positions[i][0]) * lam,
                positions[i][1] + (positions[i+1][1] - positions[i][1]) * lam,
                positions[i][2] + (positions[i+1][2] - positions[i][2]) * lam,
            )

        # Check end effector distance
        if vec_len(vec_sub(positions[-1], target_pos)) <= tolerance:
            break
    return positions
