"""
Generator: THE CREW (Robots)
Part of Grime Studio Showcase.
"""
from typing import Tuple
from engines.mesh_kernel.service import MeshService
from engines.mesh_kernel.schemas import AgentMeshInstruction, MeshObject
from engines.animation_kernel.service import AnimationService
from engines.animation_kernel.schemas import Skeleton, AgentAnimInstruction

def _create_stickman_mesh(mesh_service: MeshService, style="STANDARD") -> MeshObject:
    """
    Creates a detailed segmented robot mesh.
    Style: STANDARD (SpitBot) or BOXY (SelectaBot)
    """
    parts = []
    
    # TORSO (Chest + Hips)
    torso_kind = "CUBE" if style == "BOXY" else "CYLINDER"
    torso = mesh_service.execute_instruction(
        AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": torso_kind, "size": 1.0, "radius": 0.25, "height": 0.6})
    )
    # Scale torso for Boxy
    if style == "BOXY":
        scale = [0.4, 0.5, 0.25]
        torso.vertices = [[v[0]*scale[0], v[1]*scale[1], v[2]*scale[2]] for v in torso.vertices]
    # Move up
    torso.vertices = [[v[0], v[1]+1.3, v[2]] for v in torso.vertices]
    parts.append(torso)
    
    # HEAD
    head_kind = "CUBE" if style == "BOXY" else "SPHERE"
    head = mesh_service.execute_instruction(
        AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": head_kind, "size": 0.25, "radius": 0.15})
    )
    head.vertices = [[v[0], v[1]+1.75, v[2]] for v in head.vertices]
    parts.append(head)
    
    # HEADPHONES (Selecta Only)
    if style == "BOXY":
        ear_l = mesh_service.execute_instruction(
             AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "CYLINDER", "radius": 0.08, "height": 0.05})
        )
        ear_l.vertices = [[v[0], -v[2], v[1]] for v in ear_l.vertices] # Rotate to side
        ear_l.vertices = [[v[0]-0.15, v[1]+1.75, v[2]] for v in ear_l.vertices]
        parts.append(ear_l)
        
        ear_r = mesh_service.execute_instruction(
             AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "CYLINDER", "radius": 0.08, "height": 0.05})
        )
        ear_r.vertices = [[v[0], -v[2], v[1]] for v in ear_r.vertices] # Rotate
        ear_r.vertices = [[v[0]+0.15, v[1]+1.75, v[2]] for v in ear_r.vertices]
        parts.append(ear_r)

    # LIMBS (Simplified for Showcase V1 Geometry - usually separate meshes for rigging binding)
    # For now, we return a single merged mesh, and Auto-Rig will skin it based on proximity.
    
    # Arm Left
    arm_l = mesh_service.execute_instruction(
        AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "CYLINDER", "radius": 0.06, "height": 0.7})
    )
    arm_l.vertices = [[v[0]-0.3, v[1]+1.3, v[2]] for v in arm_l.vertices]
    parts.append(arm_l)
    
    # Arm Right
    arm_r = mesh_service.execute_instruction(
        AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "CYLINDER", "radius": 0.06, "height": 0.7})
    )
    arm_r.vertices = [[v[0]+0.3, v[1]+1.3, v[2]] for v in arm_r.vertices]
    parts.append(arm_r)
    
    # Leg Left
    leg_l = mesh_service.execute_instruction(
        AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "CYLINDER", "radius": 0.08, "height": 0.9})
    )
    leg_l.vertices = [[v[0]-0.15, v[1]+0.45, v[2]] for v in leg_l.vertices]
    parts.append(leg_l)
    
    # Leg Right
    leg_r = mesh_service.execute_instruction(
        AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "CYLINDER", "radius": 0.08, "height": 0.9})
    )
    leg_r.vertices = [[v[0]+0.15, v[1]+0.45, v[2]] for v in leg_r.vertices]
    parts.append(leg_r)

    # MERGE
    final_verts = []
    final_faces = []
    vert_offset = 0
    for p in parts:
        final_verts.extend(p.vertices)
        for f in p.faces:
            final_faces.append([i + vert_offset for i in f])
        vert_offset += len(p.vertices)
    
    mesh_id = f"mesh_robot_{style.lower()}_v1"
    final_mesh = MeshObject(id=mesh_id, vertices=final_verts, faces=final_faces, tags=["char", style])
    mesh_service._store[mesh_id] = final_mesh
    return final_mesh

def generate_selecta_bot(mesh_service: MeshService, anim_service: AnimationService) -> Tuple[str, str]:
    """Generates the DJ."""
    print("🤖 Building Selecta_Bot...")
    mesh = _create_stickman_mesh(mesh_service, style="BOXY")
    
    # Rig
    print("   Rigging Selecta_Bot...")
    # Instruct AnimService to create a skeleton. 
    # NOTE: In Phase 3 implementation, AUTO_RIG just produced a generic skeleton struct. 
    # It didn't perform actual Skin Weight calculation on the mesh (BIND_MESH).
    # For this showcase, we will invoke AUTO_RIG to get the skeleton ID.
    skeleton = anim_service.execute_instruction(AgentAnimInstruction(op_code="AUTO_RIG", params={}))
    
    # TODO: Implement BIND_MESH in Phase 2? Or manually assign weights here?
    # For now, we return IDs.
    return mesh.id, skeleton.id

def generate_spit_bot(mesh_service: MeshService, anim_service: AnimationService, variant=1) -> Tuple[str, str]:
    """Generates an MC."""
    print(f"🤖 Building Spit_Bot_0{variant}...")
    mesh = _create_stickman_mesh(mesh_service, style="STANDARD")
    # Rig
    skeleton = anim_service.execute_instruction(AgentAnimInstruction(op_code="AUTO_RIG", params={}))
    return mesh.id, skeleton.id
