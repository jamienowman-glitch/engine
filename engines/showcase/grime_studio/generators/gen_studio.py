"""
Generator: STUDIO PROPS (Speakers, Table)
Part of Grime Studio Showcase.
"""
from engines.mesh_kernel.service import MeshService
from engines.mesh_kernel.schemas import AgentMeshInstruction, MeshObject
from engines.stage_kernel.schemas import PropDefinition, PropType, Vector3

def generate_speaker(mesh_service: MeshService) -> str:
    """Generates a Studio Monitor Mesh."""
    spk_id = "mesh_speaker_monitor_v1"
    parts = []
    
    # 1. Cabinet (Box)
    cabinet = mesh_service.execute_instruction(
        AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "CUBE", "size": 1.0})
    )
    # Scale: 0.25 W, 0.4 H, 0.25 D
    scale = [0.25, 0.4, 0.25]
    cabinet.vertices = [[v[0]*scale[0], v[1]*scale[1], v[2]*scale[2]] for v in cabinet.vertices]
    parts.append(cabinet)
    
    # 2. Woofer (Cylinder)
    woofer = mesh_service.execute_instruction(
        AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "CYLINDER", "radius": 0.1, "height": 0.02})
    )
    # Rotate 90 X to face forward (Simple hack: swap Y/Z coords roughly)
    # Actually, default cylinder is Y-up. To face Z-forward, we rotate 90 X.
    # sin(90)=1, cos(90)=0. y' = -z, z' = y
    woofer.vertices = [[v[0], -v[2], v[1]] for v in woofer.vertices]
    # Move
    offset = [0.0, -0.05, 0.13] # Lower center, slightly proud of face
    woofer.vertices = [[v[0]+offset[0], v[1]+offset[1], v[2]+offset[2]] for v in woofer.vertices]
    parts.append(woofer)

    # 3. Tweeter (Smaller Cylinder)
    tweeter = mesh_service.execute_instruction(
        AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "CYLINDER", "radius": 0.03, "height": 0.02})
    )
    tweeter.vertices = [[v[0], -v[2], v[1]] for v in tweeter.vertices] # Rotate
    offset_t = [0.0, 0.12, 0.13] # Upper center
    tweeter.vertices = [[v[0]+offset_t[0], v[1]+offset_t[1], v[2]+offset_t[2]] for v in tweeter.vertices]
    parts.append(tweeter)

    # --- MERGE ---
    final_verts = []
    final_faces = []
    vert_offset = 0
    for p in parts:
        final_verts.extend(p.vertices)
        for f in p.faces:
            final_faces.append([i + vert_offset for i in f])
        vert_offset += len(p.vertices)
        
    final_mesh = MeshObject(id=spk_id, vertices=final_verts, faces=final_faces, tags=["prop", "speaker"])
    mesh_service._store[spk_id] = final_mesh
    return spk_id

def generate_table(mesh_service: MeshService) -> str:
    """Generates a DJ Table."""
    tbl_id = "mesh_table_dj_v1"
    
    # Simple slab
    table = mesh_service.execute_instruction(
        AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "CUBE", "size": 1.0})
    )
    # Scale: 2.0 W, 0.05 H, 0.8 D
    scale = [2.0, 0.05, 0.8]
    table.vertices = [[v[0]*scale[0], v[1]*scale[1], v[2]*scale[2]] for v in table.vertices]
    
    final_mesh = MeshObject(id=tbl_id, vertices=table.vertices, faces=table.faces, tags=["prop", "table"])
    mesh_service._store[tbl_id] = final_mesh
    return tbl_id

def register_studio_props(stage_service, spk_id, tbl_id):
    stage_service._prop_library["prop_speaker"] = PropDefinition(
        id="prop_speaker",
        name="Showcase Monitor",
        kind=PropType.STATIC_MESH,
        mesh_asset_id=spk_id,
        default_scale=Vector3(x=1,y=1,z=1)
    )
    stage_service._prop_library["prop_table"] = PropDefinition(
        id="prop_table",
        name="DJ Table",
        kind=PropType.STATIC_MESH,
        mesh_asset_id=tbl_id,
        default_scale=Vector3(x=1,y=1,z=1)
    )
