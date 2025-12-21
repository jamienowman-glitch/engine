"""Stage Engine Tests."""
import pytest
from engines.stage_kernel.service import StageService
from engines.stage_kernel.schemas import AgentStageInstruction
# Tests

def test_stage_spawn_prop():
    service = StageService()
    scene = service.create_empty_scene()
    
    # Spawn a Cyber Building
    instr = AgentStageInstruction(
        op_code="SPAWN_PROP",
        params={
            "prop_id": "prop_building_cyber",
            "position": [10, 0, 10]
        },
        target_scene_id=scene.id
    )
    
    node = service.execute_instruction(instr)
    
    assert node is not None
    assert "Cyber Building" in node.name
    assert node.transform.position.x == 10.0
    assert node.mesh_id == "mesh_bld_cyber_01"
    assert node.transform.scale.y == 10.0 # Default scale from library

def test_stage_light_setup():
    service = StageService()
    scene = service.create_empty_scene()
    
    # Add a Sun
    instr = AgentStageInstruction(
        op_code="SET_LIGHT",
        params={
            "type": "SUN",
            "color": [1.0, 0.9, 0.8],
            "intensity": 5.0
        },
        target_scene_id=scene.id
    )
    
    service.execute_instruction(instr)
    
    assert len(scene.lights) == 1
    light = scene.lights[0]
    assert light.kind == "directional"
    assert light.intensity == 5.0
