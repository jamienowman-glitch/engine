"""Tests for Bot Better Know 3D Presets."""
from engines.scene_engine.avatar.models import AvatarBodyPart
from engines.bot_better_know.scene3d.presets import (
    AndroidAvatarStyle,
    AndroidAvatarVariant,
    GrimeStudioStyle,
    GrimeStudioVariant,
    build_grime_pirate_rooftop_scene,
    build_android_mc_avatar,
    build_bbk_android_mc_avatar_full_gas,
    insert_android_mc_avatar,
    center_mc_spot_in_room,
    load_bbk_hero_avatar_scene_v2,
    build_bbk_beauty_environment,
    build_bbk_hero_avatar_beauty_scene,
    build_bbk_rooftop_with_constraints,
    build_bbk_hero_avatar_beauty_scene_constrained,
    build_bbk_mc_parametric_scene
)
from engines.scene_engine.core.scene_v2 import SceneV2
from engines.scene_engine.core.types import Camera


# --- Android Avatar Tests ---

def test_build_android_mc_avatar_basic():
    scene, rig = build_android_mc_avatar()
    
    assert len(scene.nodes) > 0
    assert len(scene.materials) >= 2 # Base + Accent
    
    # Check rig
    assert len(rig.bones) > 10
    
    # Check tagging
    # Flatten search
    def flatten(nodes):
        l = []
        for n in nodes:
            l.append(n)
            l.extend(flatten(n.children))
        return l
        
    all_nodes = flatten(scene.nodes)
    
    # Verify project tag
    assert any(n.meta.get("project") == "bot-better-know" for n in all_nodes)

    head = next((n for n in all_nodes if n.meta.get("body_part") == AvatarBodyPart.HEAD.value), None)
    assert head is not None
    assert head.meta.get("avatar_kind") == AndroidAvatarVariant.ANDROID_MC_V1.value
    
    torso = next((n for n in all_nodes if n.meta.get("body_part") == AvatarBodyPart.TORSO.value), None)
    assert torso is not None
    assert torso.mesh_id is not None # Should have a mesh
    
    # Check attachment slots
    # Head Top should be in rig bindings
    att_head = next((b for b in rig.attachments if "HEAD_TOP" in b.slot.value), None)
    assert att_head is not None


def test_android_style_overrides():
    style = AndroidAvatarStyle(
        head_scale=2.0,
        base_color="#ff0000"
    )
    scene, rig = build_android_mc_avatar(style)
    
    def flatten(nodes):
        l = []
        for n in nodes:
            l.append(n)
            l.extend(flatten(n.children))
        return l
    all_nodes = flatten(scene.nodes)
    
    head = next((n for n in all_nodes if n.meta.get("body_part") == AvatarBodyPart.HEAD.value), None)
    
    # Head scale should be 2.0
    assert abs(head.transform.scale.x - 2.0) < 0.01

    # Base material color
    mat_base = next((m for m in scene.materials if m.base_color.x > 0.9 and m.base_color.y < 0.1), None)
    # Red is (1,0,0). x>0.9, y<0.1 ok.
    assert mat_base is not None


def test_insert_android_mc_avatar():
    base_scene = SceneV2(id="b", nodes=[], meshes=[], materials=[], # camera=None
    )
    updated, rig = insert_android_mc_avatar(base_scene)
    
    assert len(updated.nodes) > 0
    assert rig.root_bone_id is not None


# --- Grime Environment Tests ---

def test_build_grime_pirate_rooftop_scene_basic():
    scene = build_grime_pirate_rooftop_scene()
    
    # Check Roof
    roof = next((n for n in scene.nodes if n.meta.get("env_kind") == "ROOF_SLAB"), None)
    assert roof is not None
    assert roof.meta["preset"] == GrimeStudioVariant.PIRATE_ROOFTOP_V1.value
    assert roof.meta["project"] == "bot-better-know"
    
    # Check Room Shack
    room_nodes = [n for n in scene.nodes if n.meta.get("room_role") == "pirate_radio_shack"]
    assert len(room_nodes) > 0 # Walls, floor etc
    assert room_nodes[0].meta["project"] == "bot-better-know"
    
    # Check Props
    mic = next((n for n in scene.nodes if n.meta.get("role") == "mc_spot"), None)
    assert mic is not None
    assert mic.meta["env_kind"] == "MIC_STAND"
    
    ant = next((n for n in scene.nodes if n.meta.get("role") == "pirate_broadcast_aerial"), None)
    assert ant is not None


def test_grime_preset_clutter_tags():
    style = GrimeStudioStyle(clutter_level=0.9, grime_level=0.8)
    scene = build_grime_pirate_rooftop_scene(style)
    
    clutter = next((n for n in scene.nodes if n.meta.get("env_kind") == "CLUTTER"), None)
    assert clutter is not None
    assert clutter.meta["clutter_level"] == 0.9


def test_center_mc_spot_in_room():
    scene = build_grime_pirate_rooftop_scene()
    
    # Move mic far away
    mic = next(n for n in scene.nodes if n.meta.get("role") == "mc_spot")
    original_z = mic.transform.position.z
    mic.transform.position.z = -100.0
    
    scene = center_mc_spot_in_room(scene)
    
    # Should be back near desk (Desk Z approx > 0)
    assert mic.transform.position.z > -5.0
    # And roughly original (since original builder places it well)
    assert abs(mic.transform.position.z - original_z) < 2.0


def test_build_bbk_android_mc_avatar_full_gas():
    scene, rig = build_bbk_android_mc_avatar_full_gas()
    
    # helper
    def count_nodes(nodes):
        c = 0
        for n in nodes:
            c += 1 + count_nodes(n.children)
        return c

    # 1. Check Node Count (Avatar + Floor + Camera)
    # Base avatar has ~15-20 nodes. Floor is 1. Camera is 1.
    assert count_nodes(scene.nodes) > 10
    
    # 2. Check Ground Plane
    floor_node = next((n for n in scene.nodes if n.meta.get("role") == "studio_floor"), None)
    assert floor_node is not None
    assert floor_node.meta["env_kind"] == "ROOF_SLAB"
    
    # 3. Check Camera Hint
    cam_node = next((n for n in scene.nodes if n.meta.get("role") == "camera_primary"), None)
    assert cam_node is not None
    assert cam_node.meta["target"] == "avatar_root"
    
    # 4. Check Materials (Non-default colors)
    # Default is roughly 0.2, 0.2, 0.2
    # We set base color to #1A1A1A
    # We set metallic to 0.9
    
    # Flatten materials? scene.materials is list.
    assert len(scene.materials) > 0
    mat = next((m for m in scene.materials if m.name == "AndroidBase"), None)
    assert mat is not None
    # Check metallic
    assert mat.metallic == 0.9


# --- Hero Avatar + Beauty Tests ---

def test_load_bbk_hero_avatar_scene_v2():
    scene = load_bbk_hero_avatar_scene_v2()
    
    assert len(scene.nodes) > 0
    assert len(scene.meshes) > 0
    
    # Check for tagged root
    roots = [n for n in scene.nodes if n.meta.get("role") == "hero_avatar"]
    assert len(roots) > 0
    assert roots[0].meta["project"] == "bot_better_know"


def test_build_bbk_beauty_environment():
    scene = build_bbk_beauty_environment()
    
    # Check Ground
    ground = next((n for n in scene.nodes if n.meta.get("env_kind") == "beauty_ground"), None)
    assert ground is not None
    assert ground.meta["project"] == "bot_better_know"
    
    # Check Backdrop
    backdrop = next((n for n in scene.nodes if n.meta.get("env_kind") == "beauty_backdrop"), None)
    assert backdrop is not None
    
    # Check Environment metadata
    assert scene.environment is not None
    assert scene.environment.get("kind") == "beauty_landscape"
    assert "sky_color" in scene.environment


def test_build_bbk_hero_avatar_beauty_scene():
    scene = build_bbk_hero_avatar_beauty_scene()
    
    # 1. Components Merged
    # Ground present?
    ground = next((n for n in scene.nodes if n.meta.get("env_kind") == "beauty_ground"), None)
    assert ground is not None
    
    # Avatar present?
    avatar = next((n for n in scene.nodes if n.meta.get("role") == "hero_avatar"), None)
    assert avatar is not None
    
    # 2. Camera Rig Present
    # Check Camera
    assert scene.camera is not None
    # Check Lights
    assert len(scene.lights) > 0
    
    # Verify Lights are targeted
    # Camera should be orbiting avatar (or looking at it)
    # The rig logic sets camera.target = node.position
    # We can inspect camera props if exposed, or just rely on 'create_orbit_camera_rig_for_node' being trusted/tested
    assert scene.camera.target is not None
