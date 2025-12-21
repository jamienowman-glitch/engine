"""Tests for Avatar Evolution (P15)."""

from engines.scene_engine.avatar.evolution import evolve_avatar
from engines.scene_engine.avatar.variation import randomize_avatar
from engines.scene_engine.avatar.service import build_default_avatar
from engines.scene_engine.core.scene_v2 import SceneV2
import uuid

def test_evolve_avatar():
    # 1. Create Parent
    scene, rig = build_default_avatar()
    scene.id = str(uuid.uuid4())
    
    # 2. Randomize Style (P10) to establish baseline params in meta
    scene = randomize_avatar(scene, rig, seed="parent_seed")
    parent_height = scene.nodes[0].meta["style_params"]["height"]
    
    # 3. Evolve
    child_scene, child_rig = evolve_avatar(scene, rig, mutation_rate=0.5)
    
    # 4. Verify Lineage
    lineage = child_scene.meta.get("lineage")
    assert lineage is not None
    assert lineage["parent_id"] == scene.id
    assert lineage["generation"] == 1
    
    # 5. Verify Mutation
    child_height = child_scene.nodes[0].meta["style_params"]["height"]
    
    # Should differ (randomness implies small probability of exact match, but float perturbation makes match unlikely)
    assert abs(child_height - parent_height) > 0.0001
    
    # Verify rig still valid
    assert child_rig.root_bone_id == rig.root_bone_id
