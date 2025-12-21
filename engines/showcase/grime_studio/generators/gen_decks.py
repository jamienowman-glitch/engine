"""
Generator: THE DECK (CDJ-3000 Style)
Part of Grime Studio Showcase.
"""
import uuid
from typing import List

from engines.mesh_kernel.service import MeshService
from engines.mesh_kernel.schemas import AgentMeshInstruction, MeshObject, Vector3Model
from engines.stage_kernel.schemas import PropDefinition, PropType, Vector3

def generate_deck(mesh_service: MeshService) -> str:
    """
    Generates a High-Fidelity CDJ Deck Mesh.
    Returns: The Mesh Asset ID.
    """
    deck_id = "mesh_deck_cdj_v1"
    
    # We will build this by generating parts and (conceptually) merging them.
    # Since our MeshKernel V1 doesn't have a robust 'Mesh Merge' op exposed to Agent yet,
    # we will generate the parts and simple append their geometry manually here in python
    # to create one single "Static Mesh" for the engine.
    
    parts = []
    
    # 1. BASE BODY (Box)
    # Dimensions: 329 x 118 x 453 mm (approx) -> scale to 0.32, 0.1, 0.45
    base = mesh_service.execute_instruction(
        AgentMeshInstruction(
            op_code="PRIMITIVE", 
            params={"kind": "CUBE", "size": 1.0} 
        )
    )
    # Scale Base (Non-uniform scale isn't a primitive param, so we modify vertices directly for this generator)
    # A real Agent would use a SCALE op if available.
    scale_vec = [0.35, 0.1, 0.45]
    base.vertices = [[v[0]*scale_vec[0], v[1]*scale_vec[1], v[2]*scale_vec[2]] for v in base.vertices]
    parts.append(base)
    
    # 2. PLATTER (Cylinder)
    # Jog Wheel
    platter = mesh_service.execute_instruction(
        AgentMeshInstruction(
            op_code="PRIMITIVE",
            params={"kind": "CYLINDER", "radius": 0.12, "height": 0.04}
        )
    )
    # Move Platter Up and Forward
    # Y = 0.05 (top of base) + 0.02 (half height) = 0.07
    # Z = 0.05 (forward a bit)
    offset = [0.0, 0.07, 0.05]
    platter.vertices = [[v[0]+offset[0], v[1]+offset[1], v[2]+offset[2]] for v in platter.vertices]
    parts.append(platter)
    
    # 3. SCREEN (Plane/Cube flattened)
    screen = mesh_service.execute_instruction(
        AgentMeshInstruction(
            op_code="PRIMITIVE",
            params={"kind": "CUBE", "size": 1.0}
        )
    )
    # Screen is at the back, tilted.
    # Scale: 0.25 wide, 0.02 thick, 0.15 tall
    s_scale = [0.25, 0.02, 0.15]
    # Rotate 15 deg? (Skip rotation math for now, just flat screen raised)
    screen.vertices = [[v[0]*s_scale[0], v[1]*s_scale[1], v[2]*s_scale[2]] for v in screen.vertices]
    # Move to back
    s_offset = [0.0, 0.08, -0.12]
    screen.vertices = [[v[0]+s_offset[0], v[1]+s_offset[1], v[2]+s_offset[2]] for v in screen.vertices]
    parts.append(screen)
    
    # --- MERGE INTO ONE MESH ---
    final_verts = []
    final_faces = []
    
    vert_offset = 0
    for p in parts:
        final_verts.extend(p.vertices)
        for f in p.faces:
            # Shift indices
            final_faces.append([i + vert_offset for i in f])
        vert_offset += len(p.vertices)
        
    final_mesh = MeshObject(
        id=deck_id,
        vertices=final_verts,
        faces=final_faces,
        tags=["prop", "deck"]
    )
    
    # Register in Service (Manual injection for Showcase V1)
    mesh_service._store[deck_id] = final_mesh
    return deck_id

def register_deck_prop(stage_service, deck_mesh_id):
    """Registers the Deck Prop Definition."""
    prop = PropDefinition(
        id="prop_cdj",
        name="Showcase Deck CDJ",
        kind=PropType.STATIC_MESH,
        mesh_asset_id=deck_mesh_id,
        default_scale=Vector3(x=1,y=1,z=1)
    )
    stage_service._prop_library["prop_cdj"] = prop

