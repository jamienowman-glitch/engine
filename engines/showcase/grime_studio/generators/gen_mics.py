"""
Generator: THE MIC (Handheld Dynamic Style)
Part of Grime Studio Showcase.
"""
from engines.mesh_kernel.service import MeshService
from engines.mesh_kernel.schemas import AgentMeshInstruction, MeshObject
from engines.stage_kernel.schemas import PropDefinition, PropType, Vector3

def generate_mic(mesh_service: MeshService) -> str:
    """Generates a Dynamic Mic Mesh."""
    mic_id = "mesh_mic_dynamic_v1"
    parts = []
    
    # 1. HANDLE (Cylinder, long and thin)
    handle = mesh_service.execute_instruction(
        AgentMeshInstruction(
            op_code="PRIMITIVE", 
            params={"kind": "CYLINDER", "radius": 0.02, "height": 0.18} 
        )
    )
    # Default cylinder is centered at 0,0,0.
    parts.append(handle)
    
    # 2. GRILL (Sphere, on top)
    grill = mesh_service.execute_instruction(
        AgentMeshInstruction(
            op_code="PRIMITIVE",
            params={"kind": "SPHERE", "radius": 0.03}
        )
    )
    # Move up (Half handle height 0.09 + padding)
    grill.vertices = [[v[0], v[1]+0.10, v[2]] for v in grill.vertices]
    parts.append(grill)
    
    # --- MERGE ---
    final_verts = []
    final_faces = []
    vert_offset = 0
    for p in parts:
        final_verts.extend(p.vertices)
        for f in p.faces:
            final_faces.append([i + vert_offset for i in f])
        vert_offset += len(p.vertices)
        
    final_mesh = MeshObject(
        id=mic_id,
        vertices=final_verts,
        faces=final_faces,
        tags=["prop", "mic"]
    )
    mesh_service._store[mic_id] = final_mesh
    return mic_id

def register_mic_prop(stage_service, mic_mesh_id):
    prop = PropDefinition(
        id="prop_mic_handheld",
        name="Showcase Mic Dynamic",
        kind=PropType.STATIC_MESH,
        mesh_asset_id=mic_mesh_id,
        default_scale=Vector3(x=1,y=1,z=1)
    )
    stage_service._prop_library["prop_mic_handheld"] = prop
