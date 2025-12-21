"""BBK 3D Preview Routes."""
from __future__ import annotations

from fastapi import APIRouter, UploadFile, File

from engines.bot_better_know.scene3d.presets import (
    build_grime_pirate_rooftop_scene,
    build_android_mc_avatar,
    build_bbk_android_mc_avatar_full_gas,
    build_bbk_hero_avatar_beauty_scene,
    AndroidAvatarStyle,
)
from engines.scene_engine.avatar.style import (
    AvatarStyleParams,
    apply_avatar_style,
    BodyBuild,
)
from engines.scene_engine.core.adapter import scene_v2_to_scene
from engines.scene_engine.core.scene_v2 import SceneV2

router = APIRouter()


@router.get("/bbk/3d-preview/avatar-full-gas")
async def get_avatar_full_gas():
    """Generates a 'Full Gas' showcase of the Android MC avatar."""
    scene, rig = build_bbk_android_mc_avatar_full_gas()
    return scene_v2_to_scene(scene)
    return scene_v2_to_scene(scene)


@router.get("/bbk/3d-preview/hero-avatar-beauty")
async def get_hero_avatar_beauty():
    """Generates the Hero Avatar + Beauty Environment scene (Dev Only)."""
    scene = build_bbk_hero_avatar_beauty_scene()
    return scene_v2_to_scene(scene)

@router.get("/bbk/3d-preview/android-on-rooftop")
async def get_android_on_rooftop():
    """Generates a preview scene with Android MC standing on the Rooftop."""
    
    # 1. Build Environment
    scene = build_grime_pirate_rooftop_scene()
    
    # 2. Build Avatar with Style
    # Standard android visual style
    android_style = AndroidAvatarStyle(
        base_color="#333333",
        accent_color="#FF00FF", # Cyberpunk pink
        metallicity=0.8,
        roughness=0.2
    )
    
    # Generic physics/shape style
    generic_style = AvatarStyleParams(
        height=1.85, 
        body_build=BodyBuild.HEAVY, # Make him chunky
        has_shoulder_pads=True      # Just a flag for now
    )
    
    # Create avatar scene
    avatar_scene, rig = build_android_mc_avatar(android_style)
    
    # Apply generic style overrides (shape)
    avatar_scene = apply_avatar_style(avatar_scene, rig, generic_style)
    
    # 3. Position Avatar
    # Find MC Spot in room
    mc_spot = next((n for n in scene.nodes if n.meta.get("role") == "mc_spot"), None)
    
    if mc_spot:
        # Parent avatar root to spot
        # Or just copy transform. Usually referencing spot is better.
        # But for flattened V1 adapter, we might need absolute world pos if hierarchy isn't fully robust.
        # Adapter handles simple translation composition.
        
        # Let's attach the specific avatar root bone node to the scene
        # The avatar scene root is usually just a container or the pelvis.
        # build_default_avatar returns a scene with a root node (id="root_node" maybe, or random)
        
        # We'll just take all avatar nodes and putting them under a new container placed at the spot
        import uuid
        from engines.scene_engine.core.scene_v2 import SceneNodeV2
        from engines.scene_engine.core.geometry import Transform, Vector3
        
        container = SceneNodeV2(
            id=f"avatar_container_{uuid.uuid4().hex[:8]}",
            name="AvatarContainer",
            transform=mc_spot.transform, # Match spot transform
            children=avatar_scene.nodes
        )
        
        # Reset avatar root transforms relative to container if needed?
        # Usually avatar root is at 0,0,0.
        # But wait, mc_spot transform is relative to its parent (mic stand or room).
        # We need world position for safety if we just append to root.
        
        # Let's just append avatar nodes to the scene root but offset them manually for now, 
        # or properly parenting them to the room if we knew the ID.
        # Simpler: Just override the avatar root node's transform to match what we think the MC spot is.
        # MC spot is: 
        #   Room Origin + Offset 
        #   We don't easily know absolute pos without traversing.
        
        # Let's append the container to the scene root, but we need to know the spot's world position 
        # approximately.
        # In `build_grime_pirate_rooftop_scene`: 
        #   room origin = (2,0,2)
        #   desk pos = (2, 0.4, 3.4) (approx)
        #   mc pos = (2, 0.7, 2.2) (approx)
        
        # Let's just set the container to (2.0, 0.0, 2.2) manually for the preview to be safe/easy
        container.transform = Transform(
            position=Vector3(x=2.0, y=0.0, z=2.2), # Standing on floor roughly
            scale=Vector3(x=1, y=1, z=1),
            rotation=mc_spot.transform.rotation # Inherit rotation if compatible
        )
        
        scene.nodes.append(container)
        scene.meshes.extend(avatar_scene.meshes)
        scene.materials.extend(avatar_scene.materials)
        
    else:
        # Fallback: just add at origin
        scene.nodes.extend(avatar_scene.nodes)
        scene.meshes.extend(avatar_scene.meshes)
        scene.materials.extend(avatar_scene.materials)

    # 4. Adapt to Legacy
    legacy_scene = scene_v2_to_scene(scene)
    
    return legacy_scene
    return legacy_scene


@router.post("/bbk/3d-preview/gltf-avatar")
async def upload_gltf_avatar(file: UploadFile = File(...)):
    """Uploads a .glb file and returns a Hero Scene with it."""
    # 1. Read Bytes
    content = await file.read()
    
    # 2. Convert to SceneV2
    from engines.scene_engine.io.gltf_import import gltf_bytes_to_scene_v2
    avatar_scene = gltf_bytes_to_scene_v2(content)
    
    # 3. Create Environment
    from engines.bot_better_know.scene3d.presets import build_bbk_beauty_environment
    env_scene = build_bbk_beauty_environment()
    
    # 4. Merge
    import uuid
    final_scene = SceneV2(
        id=uuid.uuid4().hex,
        nodes=env_scene.nodes + avatar_scene.nodes,
        meshes=env_scene.meshes + avatar_scene.meshes,
        materials=env_scene.materials + avatar_scene.materials,
        environment=env_scene.environment
    )
    
    # 5. Find Root & Attach Rig
    # Assuming first node from glTF is root?
    # glTF import usually adds nodes to list.
    # We should pick the first node from avatar_scene.nodes as target.
    if avatar_scene.nodes:
        target_root = avatar_scene.nodes[0]
        
        # Tag it so we know
        target_root.meta["role"] = "uploaded_avatar"
        
        from engines.scene_engine.camera.service import create_orbit_camera_rig_for_node, attach_camera_rig_to_scene
        from engines.scene_engine.camera.models import CameraShotKind
        
        rig = create_orbit_camera_rig_for_node(
            final_scene, 
            target_root.id, 
            distance=3.5, 
            height=1.5,
            shot_kind=CameraShotKind.FULL_BODY
        )
        final_scene = attach_camera_rig_to_scene(final_scene, rig)
        
    return scene_v2_to_scene(final_scene)
