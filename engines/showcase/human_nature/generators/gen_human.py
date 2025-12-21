"""
GENERATOR: HUMAN CHARACTER
--------------------------
Generates a stylized Low-Poly Human (Suit, Tie, Face).
"""
import uuid
from typing import Dict, Tuple, List

from engines.mesh_kernel.service import MeshService
from engines.mesh_kernel.schemas import AgentMeshInstruction
from engines.animation_kernel.service import AnimationService

# Return Type: (SkeletonID, Dict[BoneName, MeshID])
# We return a map of which mesh attaches to which bone.

def generate_human(mesh_engine: MeshService, anim_engine: AnimationService, variant: int = 0) -> Tuple[str, Dict[str, str]]:
    """
    Generates a Human Character.
    Returns (skeleton_id, {bone_name: mesh_id}).
    """
    # 1. Create Skeleton
    # Uses the new AUTO_RIG with legs
    # TODO: We might want custom rig if AUTO_RIG isn't flexible enough, but we updated AUTO_RIG in service.
    # So we just trigger it.
    skel = anim_engine.execute_instruction(
        type("Instruction", (object,), {
            "op_code": "AUTO_RIG", 
            "params": {}, 
            "target_skeleton_id": None
        })()
    )
    # The helper above sends an object with attributes matching schema expected by service
    # Actually service expects AgentAnimInstruction (Pydantic).
    # Let's import the schema to be safe.
    from engines.animation_kernel.schemas import AgentAnimInstruction
    skel = anim_engine.execute_instruction(AgentAnimInstruction(op_code="AUTO_RIG", params={}))
    
    parts_map = {} # bone_id -> mesh_id
    
    # 2. Generate Body Parts (Primitives)
    
    # --- HEAD ---
    # Sphere + Nose
    # We can use boolean merge or just group them.
    # For now, let's just make the Head Sphere.
    # User wanted "Clay nose... blonde hair".
    # We'll rely on Materials for color.
    # Geometry: Sphere.
    head_mesh = mesh_engine.execute_instruction(AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "SPHERE", "radius": 0.12, "lat_bands": 12, "long_bands": 12}))
    head_mesh.id = f"human_head_{variant}"
    mesh_engine._store[head_mesh.id] = head_mesh
    parts_map["head"] = head_mesh.id
    
    # --- TORSO (Suit) ---
    # Box
    # Spine bone is from 0.9 to 1.4 (Length 0.5).
    # Width ~ 0.4. Depth ~ 0.2.
    torso_mesh = mesh_engine.execute_instruction(AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "CUBE", "size": 1.0})) # Scale later or separate dims? CUBE takes size.
    # We need to scale vertices to make it a box 0.4x0.5x0.2.
    # Primitive ops return standard cube size 1.
    # We can transform vertices in place here.
    _scale_mesh(torso_mesh, 0.4, 0.5, 0.2)
    torso_mesh.id = f"human_torso_{variant}"
    mesh_engine._store[torso_mesh.id] = torso_mesh
    parts_map["spine"] = torso_mesh.id
    
    # --- LIMBS (Capsules) ---
    
    # Function to make limb
    def make_limb(bone_name, radius, length):
        mesh = mesh_engine.execute_instruction(AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "CAPSULE", "radius": radius, "length": length}))
        # orient? Capsule is Y-up centered.
        # Bones are Y-up (implied by auto rig positions).
        mesh.id = f"human_{bone_name}_{variant}"
        mesh_engine._store[mesh.id] = mesh
        parts_map[bone_name] = mesh.id

    # Arms
    # Arm Length 0.3. Radius 0.05.
    make_limb("arm_l", 0.05, 0.3)
    make_limb("arm_r", 0.05, 0.3)
    make_limb("forearm_l", 0.04, 0.25)
    make_limb("forearm_r", 0.04, 0.25)
    
    # Legs
    # Thigh Length 0.4. Radius 0.07.
    make_limb("thigh_l", 0.07, 0.4)
    make_limb("thigh_r", 0.07, 0.4)
    # Calf Length 0.4. Radius 0.06.
    make_limb("calf_l", 0.06, 0.4)
    make_limb("calf_r", 0.06, 0.4)
    
    # Hand/Feet (Boxes)
    def make_box(bone_name, w, h, d):
        mesh = mesh_engine.execute_instruction(AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "CUBE", "size": 1.0}))
        _scale_mesh(mesh, w, h, d)
        mesh.id = f"human_{bone_name}_{variant}"
        mesh_engine._store[mesh.id] = mesh
        parts_map[bone_name] = mesh.id # Need to map to nearest bone or create "hand" bone?
        # Auto Rig doesn't have Hand/Foot bones implicitly named 'hand'? 
        # It has 'foot_l/r' (which is the ankle/foot bone).
        # It ends at 'forearm'.
        # We'll attach Hands to forearm for now or just rely on forearm capsule being long enough.
        # Let's attach 'foot' mesh to 'foot' bone.
    
    make_box("foot_l", 0.1, 0.1, 0.2) # Shoe
    make_box("foot_r", 0.1, 0.1, 0.2)
    
    # --- TIE ---
    # Chain of meshes?
    # Or just one mesh attached to Spine.
    # User wants "Flapping". This implies physics.
    # Generative Tie: A separate chain of bones? 
    # Our Auto Rig won't support it.
    # We will simulate it visually in Director by spawning "Tie Segments" and rotating them in update loop.
    # We'll generate the meshes here.
    for i in range(3):
        tie_mesh = mesh_engine.execute_instruction(AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "CUBE", "size": 1.0}))
        _scale_mesh(tie_mesh, 0.08, 0.15, 0.02)
        tie_mesh.id = f"human_tie_{i}_{variant}"
        mesh_engine._store[tie_mesh.id] = tie_mesh
        parts_map[f"tie_{i}"] = tie_mesh.id # Virtual bone name

    return skel.id, parts_map

def _scale_mesh(mesh, sx, sy, sz):
    for i in range(len(mesh.vertices)):
        mesh.vertices[i][0] *= sx
        mesh.vertices[i][1] *= sy
        mesh.vertices[i][2] *= sz

