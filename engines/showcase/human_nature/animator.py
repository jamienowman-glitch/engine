"""
ANIMATOR: HUMAN NATURE
----------------------
Procedural Motion Logic (Walk Cycle, Wind).
"""
import math
import random
from typing import Dict, List, Tuple

# Helper: Euler to Quat
def euler_to_quat(x_deg, y_deg, z_deg) -> List[float]:
    # Angles in degrees -> radians
    ex = math.radians(x_deg)
    ey = math.radians(y_deg)
    ez = math.radians(z_deg)
    
    # Standard conversion
    c1 = math.cos(ey/2)
    s1 = math.sin(ey/2)
    c2 = math.cos(ez/2)
    s2 = math.sin(ez/2)
    c3 = math.cos(ex/2)
    s3 = math.sin(ex/2)
    
    c1c2 = c1*c2
    s1s2 = s1*s2
    
    w = c1c2*c3 - s1s2*s3
    x = c1c2*s3 + s1s2*c3
    y = s1*c2*c3 + c1*s2*s3
    z = c1*s2*c3 - s1*c2*s3
    
    return [x, y, z, w]

def evaluate_walk_cycle(time: float) -> Dict[str, List[float]]:
    """
    Returns pose {bone_id: [x,y,z,w]} for a walk cycle.
    """
    pose = {}
    
    # 1.5 Hz cycle
    cycle_speed = 1.5 * (math.pi * 2)
    phase = time * cycle_speed
    
    # --- LEGS ---
    # Thigh Swing (X-axis)
    # Left Forward at phase=0
    thigh_range = 30
    thigh_l_x = math.sin(phase) * thigh_range
    thigh_r_x = math.sin(phase + math.pi) * thigh_range
    
    pose["thigh_l"] = euler_to_quat(thigh_l_x, 0, 0)
    pose["thigh_r"] = euler_to_quat(thigh_r_x, 0, 0)
    
    # Calves (Knee Flex) - only flex back (positive X?)
    # Knee bends when leg is lifting/swinging through.
    # Simple approximations:
    # If thigh moving forward, knee relatively straight.
    # If thigh moving back -> lift -> knee bends.
    # Let's offset phase.
    knee_range = 40
    calf_l_x = max(0, math.sin(phase - 1.5) * knee_range) 
    calf_r_x = max(0, math.sin(phase + math.pi - 1.5) * knee_range)
    
    pose["calf_l"] = euler_to_quat(calf_l_x, 0, 0)
    pose["calf_r"] = euler_to_quat(calf_r_x, 0, 0)
    
    # Feet (Ankle) - Keep somewhat flat
    pose["foot_l"] = euler_to_quat(math.sin(phase)*10, 0, 0)
    pose["foot_r"] = euler_to_quat(math.sin(phase + math.pi)*10, 0, 0)
    
    # --- ARMS ---
    # Opposite to legs
    shoulder_range = 20
    arm_l_x = math.sin(phase + math.pi) * shoulder_range
    arm_r_x = math.sin(phase) * shoulder_range
    
    pose["shoulder_l"] = euler_to_quat(arm_l_x, 0, 0)
    pose["shoulder_r"] = euler_to_quat(arm_r_x, 0, 0)
    
    # Elbows - slight flex
    pose["arm_l"] = euler_to_quat(30 + math.sin(phase)*10, 0, 0) 
    pose["arm_r"] = euler_to_quat(30 + math.sin(phase + math.pi)*10, 0, 0) 
    
    # --- SPINE/HEAD ---
    # Bobbing and Sway
    pose["spine"] = euler_to_quat(0, math.sin(phase)*5, 0) # Rotate Y
    pose["head"] = euler_to_quat(0, -math.sin(phase)*5, 0) # Counter rotate
    
    # Root Motion (Vertical Bob)
    # This needs to be applied to position, not rotation.
    # The Animator currently returns Rotations. 
    # Director will handle root pos bob.
    
    return pose

def evaluate_wind_tie(time: float, segments: int = 3) -> Dict[str, List[float]]:
    """
    Returns rotations for tie segments simulating wind.
    """
    pose = {}
    
    # Wind frequency
    wind_freq = 5.0
    
    for i in range(segments):
        # Noise factor
        noise = math.sin(time * wind_freq + i) + math.cos(time * wind_freq * 0.5)
        angle = 20 + noise * 15 # Flapping range
        
        # Tie bends back (X) and twists (Y)
        pose[f"tie_{i}"] = euler_to_quat(angle, noise * 5, 0)
        
    return pose
