"""Material Service for Phase 2."""
from typing import Dict, Optional, List
import uuid

from engines.material_kernel.schemas import (
    AgentMaterialInstruction, PBRMaterial, MaterialOpCode
)
# In a real app, we would import MeshService to fetch the mesh.
# For V1 decoupling, we might pass the mesh object in, or use a shared registry.
# Here we assume we receive a 'context' (the MeshObject) to modify.
from engines.mesh_kernel.schemas import MeshObject

class MaterialService:
    def __init__(self):
        self._library: Dict[str, PBRMaterial] = {}
        self._init_presets()

    def _init_presets(self):
        """Load some built-in materials."""
        presets = [
            PBRMaterial(id="mat_clay", name="Clay", base_color=[0.5, 0.5, 0.5, 1.0], roughness=0.8),
            PBRMaterial(id="mat_skin", name="Skin", base_color=[0.8, 0.6, 0.5, 1.0], roughness=0.4, metallic=0.0),
            PBRMaterial(id="mat_gold", name="Gold", base_color=[1.0, 0.8, 0.0, 1.0], roughness=0.1, metallic=1.0),
            PBRMaterial(id="mat_red_plastic", name="Red Plastic", base_color=[1.0, 0.0, 0.0, 1.0], roughness=0.2),
        ]
        for mat in presets:
            self._library[mat.id] = mat

    def execute_instruction(self, instruction: AgentMaterialInstruction, target_mesh: Optional[MeshObject]) -> Optional[PBRMaterial]:
        """
        Executes a material instruction.
        Returns the Applied Material if successful.
        """
        op = instruction.op_code.upper()
        params = instruction.params
        
        if op == "CREATE":
            # Create a new custom material
            mat = PBRMaterial(
                id=str(uuid.uuid4()),
                name=str(params.get("name", "CustomMaterial")),
                base_color=params.get("base_color", [1.0, 1.0, 1.0, 1.0]),
                roughness=params.get("roughness", 0.5),
                metallic=params.get("metallic", 0.0)
            )
            self._library[mat.id] = mat
            return mat

        if not target_mesh:
            return None # Cannot apply without target

        if op == "APPLY_PRESET":
            # Apply to WHOLE mesh (or specific faces if region param exists?)
            # Let's assume APPLY_PRESET is global if no region.
            mat_id = str(params.get("material_id", ""))
            
            # Lookup by ID or Name
            found_mat = self._library.get(mat_id)
            if not found_mat:
                # Try finding by name
                for m in self._library.values():
                    if m.name.lower() == mat_id.lower():
                        found_mat = m
                        break
            
            if found_mat:
                # Assign global (all faces)
                all_faces = list(range(len(target_mesh.faces)))
                target_mesh.material_groups[found_mat.id] = all_faces
                target_mesh.tags.append(f"material:{found_mat.name}")
                return found_mat
                
        elif op == "PAINT_REGION":
            # Paint specific face indices
            mat_id = str(params.get("material_id", ""))
            face_indices = params.get("face_indices", [])
            
            found_mat = self._library.get(mat_id)
            if found_mat and isinstance(face_indices, list):
                # We need to handle overwriting?
                # For V1: Just add to the group. A face might end up in multiple groups?
                # Ideally, a face has 1 material.
                # Remove these faces from other groups
                for k in target_mesh.material_groups:
                    target_mesh.material_groups[k] = [f for f in target_mesh.material_groups[k] if f not in face_indices]
                
                # Add to new group
                if found_mat.id not in target_mesh.material_groups:
                    target_mesh.material_groups[found_mat.id] = []
                target_mesh.material_groups[found_mat.id].extend(face_indices)
                return found_mat
                
        return None
