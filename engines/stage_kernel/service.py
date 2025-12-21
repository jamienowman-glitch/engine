"""Stage Service for Phase 4."""
import uuid
import copy
from typing import Dict, Optional, List

from engines.stage_kernel.schemas import (
    AgentStageInstruction, PropDefinition, StageOpCode, PropType
)
# Integration with Scene Engine
from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2
from engines.scene_engine.core.geometry import Transform, Vector3, Quaternion
from engines.scene_engine.camera.models import Light, LightKind

class StageService:
    def __init__(self):
        self._prop_library: Dict[str, PropDefinition] = {}
        self._init_library()
        self._active_scenes: Dict[str, SceneV2] = {}

    def _init_library(self):
        """Populate built-in props."""
        # Generic buildings/trees that map to some mesh Asset ID
        self._prop_library["prop_tree_pine"] = PropDefinition(
            id="prop_tree_pine", name="Pine Tree", kind=PropType.STATIC_MESH, 
            mesh_asset_id="mesh_tree_pine_v1"
        )
        self._prop_library["prop_building_cyber"] = PropDefinition(
            id="prop_building_cyber", name="Cyber Building", kind=PropType.STATIC_MESH,
            mesh_asset_id="mesh_bld_cyber_01",
            default_scale=Vector3(x=5,y=10,z=5)
        )
        self._prop_library["prop_floor_tile"] = PropDefinition(
            id="prop_floor_tile", name="Concrete Floor", kind=PropType.STATIC_MESH,
            mesh_asset_id="mesh_floor_tile_01"
        )

    def create_empty_scene(self) -> SceneV2:
        new_id = str(uuid.uuid4())
        scene = SceneV2(id=new_id)
        self._active_scenes[new_id] = scene
        return scene

    def execute_instruction(self, instruction: AgentStageInstruction, target_scene_id: Optional[str] = None) -> Optional[SceneNodeV2]:
        """
        Executes a stage instruction.
        Returns the created Node (for SPAWN) or None.
        """
        op = instruction.op_code.upper()
        params = instruction.params
        
        # Resolve scene
        s_id = target_scene_id or instruction.target_scene_id
        if not s_id or s_id not in self._active_scenes:
            return None
        
        scene = self._active_scenes[s_id]

        if op == "SPAWN_PROP":
            prop_id = params.get("prop_id")
            pos = params.get("position", [0,0,0])
            rot = params.get("rotation", [0,0,0,1]) # [x,y,z,w] Quaternion
            
            # Lookup Prop
            prop_def = self._prop_library.get(prop_id)
            if not prop_def:
                return None
            
            # Create Node
            node_id = str(uuid.uuid4())
            new_node = SceneNodeV2(
                id=node_id,
                name=f"{prop_def.name}_{node_id[:4]}",
                transform=Transform(
                    position=Vector3(x=pos[0], y=pos[1], z=pos[2]),
                    rotation=Quaternion(x=rot[0], y=rot[1], z=rot[2], w=rot[3]),
                    scale=prop_def.default_scale
                ),
                mesh_id=prop_def.mesh_asset_id
            )
            scene.nodes.append(new_node)
            return new_node

        elif op == "SET_LIGHT":
            kind_str = params.get("type", "POINT").upper()
            pos = params.get("position", [0,10,0])
            intensity = params.get("intensity", 1.0)
            color = params.get("color", [1,1,1])
            
            l_kind = LightKind.POINT
            if kind_str == "SUN": l_kind = LightKind.DIRECTIONAL
            elif kind_str == "SPOT": l_kind = LightKind.SPOT
            
            light = Light(
                id=str(uuid.uuid4()),
                kind=l_kind,
                position=Vector3(x=pos[0], y=pos[1], z=pos[2]),
                intensity=intensity,
                color=Vector3(x=color[0], y=color[1], z=color[2])
            )
            scene.lights.append(light)
            return None # Or return light object wrapper?
            
        return None
