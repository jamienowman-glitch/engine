"""
Tests for scene export determinism and content (GLTF).

Ensures: exported glTF contains nodes/meshes and repeated exports on the same input are deterministic.
"""
from engines.scene_engine.avatar.service import build_default_avatar
from engines.scene_engine.export.service import export_scene
import json


def test_export_scene_contains_meshes_and_nodes():
    scene, rig = build_default_avatar()
    exported = export_scene(scene)

    assert "meshes" in exported
    assert "nodes" in exported
    assert exported.get("buffers") and exported["buffers"][0]["byteLength"] > 0


def test_export_scene_is_deterministic_for_same_input():
    scene, rig = build_default_avatar()
    # Export twice using the same in-memory scene object
    first = export_scene(scene)
    second = export_scene(scene)

    # Serialize deterministically and compare
    s1 = json.dumps(first, sort_keys=True)
    s2 = json.dumps(second, sort_keys=True)

    assert s1 == s2
    assert s1.count("meshes") > 0


def test_export_scene_has_stable_hash_across_runs():
    import hashlib

    scene, rig = build_default_avatar()
    a = export_scene(scene)
    b = export_scene(scene)

    sa = json.dumps(a, sort_keys=True).encode("utf-8")
    sb = json.dumps(b, sort_keys=True).encode("utf-8")

    ha = hashlib.sha256(sa).hexdigest()
    hb = hashlib.sha256(sb).hexdigest()

    assert ha == hb
    assert ha != ""


def test_export_includes_rig_node_ids():
    scene, rig = build_default_avatar()
    exported = export_scene(scene)

    node_names = {n["name"] for n in exported.get("nodes", [])}

    # AvatarRigDefinition has bones referencing scene node IDs; ensure each node_id exists in export
    for b in rig.bones:
        assert b.node_id in node_names


def test_export_includes_scene_meta_extras():
    scene, rig = build_default_avatar()
    # Attach non-volatile metadata
    scene.meta["export_info"] = {"avatar_id": "ava-123", "format": "gltf"}

    exported = export_scene(scene)
    assert "extras" in exported
    assert exported["extras"].get("export_info", {}).get("avatar_id") == "ava-123"


def test_export_handles_non_serializable_meta_gracefully():
    scene, rig = build_default_avatar()
    # Attach a non-serializable object
    scene.meta["weird"] = object()

    # Export should still return a dict and include the meta (it may not be JSON-serializable)
    exported = export_scene(scene)
    assert isinstance(exported, dict)
    assert "extras" in exported
    assert "weird" in exported["extras"]
