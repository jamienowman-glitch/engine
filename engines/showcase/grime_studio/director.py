import json
import math
import random
import sys
import os
sys.path.append(os.getcwd())
from typing import List, Dict

# Engines
from engines.mesh_kernel.service import MeshService
from engines.mesh_kernel.schemas import AgentMeshInstruction
from engines.stage_kernel.service import StageService
from engines.stage_kernel.schemas import AgentStageInstruction
from engines.animation_kernel.service import AnimationService
from engines.animation_kernel.schemas import AgentAnimInstruction
from engines.material_kernel.service import MaterialService
from engines.material_kernel.schemas import AgentMaterialInstruction

# Generators
from engines.showcase.grime_studio.generators import gen_decks, gen_mics, gen_studio, gen_robots

def run_show():
    print("🎬 ACTION: Grime Studio Sequence Started...")
    
    # 1. INIT ENGINES
    mesh_engine = MeshService()
    mat_engine = MaterialService()
    anim_engine = AnimationService()
    stage_engine = StageService()
    scene = stage_engine.create_empty_scene()
    
    # 2. ASSET GENERATION (The Kit)
    print("🔨 PROP SHOP: Building Decks, Amps, Mics...")
    deck_id = gen_decks.generate_deck(mesh_engine)
    gen_decks.register_deck_prop(stage_engine, deck_id)
    
    mic_id = gen_mics.generate_mic(mesh_engine)
    gen_mics.register_mic_prop(stage_engine, mic_id)
    
    spk_id = gen_studio.generate_speaker(mesh_engine)
    tbl_id = gen_studio.generate_table(mesh_engine)
    gen_studio.register_studio_props(stage_engine, spk_id, tbl_id)
    
    # 3. CAST GENERATION (The Crew)
    print("🧬 BIO LAB: Cloning Robots...")
    # NOTE: In Showcase V1 we treated Robots as single Mesh props.
    # For V2 "Puppet" logic, we need to know the parts to animate them.
    # Our gen_robots currently returns a single MERGED mesh.
    # To enable the "Part Animation" without rewriting gen_robots completely, 
    # we will rely on the "Skeleton" bone transforms to drive the mesh in the viewer.
    # The viewer (showcase.html) will receive bone data.
    # BUT wait, our viewer doesn't support skinning yet.
    # Workaround: We will use the BONE NODES as visible entities if possible? 
    # Or just spawn the robot mesh and rotate it (FK) like before?
    # No, user wants detail.
    # Let's use the Single Mesh but rely on the Skeleton visualization in the viewer? 
    # Or actually spawn parts?
    
    # DECISION: For this script, we will continue to use the SINGLE MESH robot for the main body.
    # But we will animate the ROBOT ROOT dynamically.
    # And we will spawn the MIC as a separate prop and parent it?
    
    # Let's generate the robots:
    dj_mesh_id, dj_skel_id = gen_robots.generate_selecta_bot(mesh_engine, anim_engine)
    mc1_mesh_id, mc1_skel_id = gen_robots.generate_spit_bot(mesh_engine, anim_engine, variant=1)
    # Register them as props (hacky but works for stage service)
    from engines.stage_kernel.schemas import PropDefinition, PropType, Vector3
    stage_engine._prop_library["actor_dj"] = PropDefinition(id="actor_dj", name="DJ Selecta", kind=PropType.STATIC_MESH, mesh_asset_id=dj_mesh_id)
    stage_engine._prop_library["actor_mc1"] = PropDefinition(id="actor_mc1", name="MC Spit 1", kind=PropType.STATIC_MESH, mesh_asset_id=mc1_mesh_id)

    # 4. MATERIALS (The Paint)
    print("🎨 PAINT SHOP: Mixing Colours...")
    # Studio Walls (Bright Red)
    mat_wall_red = mat_engine.execute_instruction(AgentMaterialInstruction(op_code="CREATE", params={"name": "StudioRed", "base_color": [0.8, 0.1, 0.1, 1], "roughness": 0.5}), target_mesh=None)
    # Floor (Lighter Grey)
    mat_floor = mat_engine.execute_instruction(AgentMaterialInstruction(op_code="CREATE", params={"name": "StudioFloor", "base_color": [0.2, 0.2, 0.2, 1], "roughness": 0.5}), target_mesh=None)
    # Chrome (Robots) - Brighter
    mat_chrome = mat_engine.execute_instruction(AgentMaterialInstruction(op_code="CREATE", params={"name": "Chrome", "base_color": [0.9, 0.9, 0.95, 1], "metallic": 0.9, "roughness": 0.1}), target_mesh=None)
    # LED Blue (Decks)
    mat_led = mat_engine.execute_instruction(AgentMaterialInstruction(op_code="CREATE", params={"name": "LED", "base_color": [0, 1, 1, 1], "emissive": [0, 1, 1]}), target_mesh=None)
    
    # Assign materials
    mat_engine.execute_instruction(AgentMaterialInstruction(op_code="APPLY_PRESET", params={"material_id": mat_chrome.id}, target_id=dj_mesh_id), target_mesh=mesh_engine._store[dj_mesh_id])
    mat_engine.execute_instruction(AgentMaterialInstruction(op_code="APPLY_PRESET", params={"material_id": mat_chrome.id}, target_id=mc1_mesh_id), target_mesh=mesh_engine._store[mc1_mesh_id])

    # 5. SET DRESSING (The Stage)
    print("🏗️ SET CONSTRUCTION: The Red Room...")
    stages = stage_engine
    sid = scene.id
    
    # Quick Generic Box Mesh
    wall_mesh = mesh_engine.execute_instruction(AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "CUBE", "size": 1.0}))
    wall_mesh.id = "mesh_wall_generic"
    mesh_engine._store[wall_mesh.id] = wall_mesh
    stages._prop_library["prop_wall"] = PropDefinition(id="prop_wall", name="Generic Wall", kind=PropType.STATIC_MESH, mesh_asset_id=wall_mesh.id)

    # Red Box Mesh
    red_wall_mesh = mesh_engine.execute_instruction(AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "CUBE", "size": 1.0}))
    red_wall_mesh.id = "mesh_wall_red"
    mesh_engine._store[red_wall_mesh.id] = red_wall_mesh
    stages._prop_library["prop_wall_red"] = PropDefinition(id="prop_wall_red", name="Red Wall", kind=PropType.STATIC_MESH, mesh_asset_id=red_wall_mesh.id)

    # Floor
    stages.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "prop_wall", "position": [0,-1,0], "scale": [12, 0.1, 12]}, target_scene_id=sid))
    
    # Walls (Slightly further out to let light bounce)
    stages.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "prop_wall_red", "position": [0, 4, -6], "scale": [14, 10, 0.5]}, target_scene_id=sid)) # Back
    stages.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "prop_wall_red", "position": [6, 4, 0], "scale": [0.5, 10, 14]}, target_scene_id=sid)) # Right
    stages.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "prop_wall_red", "position": [-6, 4, 0], "scale": [0.5, 10, 14]}, target_scene_id=sid)) # Left
    stages.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "prop_wall", "position": [0, 9, 0], "scale": [14, 0.5, 14]}, target_scene_id=sid)) # Ceiling

    # DJ Table
    stages.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "prop_table", "position": [0, 0.8, -2]}, target_scene_id=sid))
    # Decks
    stages.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "prop_cdj", "position": [-0.6, 0.85, -2]}, target_scene_id=sid)) # Left
    stages.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "prop_cdj", "position": [0.6, 0.85, -2]}, target_scene_id=sid)) # Right
    stages.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "prop_cdj", "position": [0, 0.85, -2]}, target_scene_id=sid)) # Mixer
    # Speakers
    stages.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "prop_speaker", "position": [-1.5, 0, -2]}, target_scene_id=sid))
    stages.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "prop_speaker", "position": [1.5, 0, -2]}, target_scene_id=sid))
    
    # Actors
    stages.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "actor_dj", "position": [0, 0, -3]}, target_scene_id=sid))
    stages.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "actor_mc1", "position": [1, 0, 1], "rotation": [0, -0.707, 0, 0.707]}, target_scene_id=sid))

    # Lighting (High Key)
    # Add Ambient/Hemisphere logic in JS template, but here we set our Scene lights.
    # We will abuse our "SET_LIGHT" to add a massive Area-like point light overhead.
    stages.execute_instruction(AgentStageInstruction(op_code="SET_LIGHT", params={"type": "POINT", "color": [1.0, 1.0, 1.0], "intensity": 80, "position": [0, 8, 2]}, target_scene_id=sid)) # Overhead flood
    stages.execute_instruction(AgentStageInstruction(op_code="SET_LIGHT", params={"type": "POINT", "color": [1.0, 0.3, 0.3], "intensity": 50, "position": [-4, 5, 4]}, target_scene_id=sid)) # Warm Fill
    stages.execute_instruction(AgentStageInstruction(op_code="SET_LIGHT", params={"type": "POINT", "color": [0.3, 0.3, 1.0], "intensity": 50, "position": [4, 5, 4]}, target_scene_id=sid)) # Cool Fill
    
    # 6. ANIMATION LOOP (The Performance)
    print("🎥 ACTION: Recording 120 frames...")
    frames_data = []
    
    # Coordinates
    deck_l_pos = [-0.6, 0.9, -2.0] # World space target for Hand
    mic_mouth_pos = [1.0, 1.6, 1.0] # MC Head position approx
    
    total_frames = 120
    for f in range(total_frames):
        t = f / 30.0 # 30 FPS
        
        frame_snapshot = {}
        
        # DJ LOGIC: Reach for Deck Left
        # DJ Root is at (0,0,-3). Shoulder is at (-0.2, 1.25, -3) approx relative to root.
        # We need IK to solve relative to root? No, IK solver takes world coords relative to shoulder?
        # Our IK solver takes (RootPos, TargetPos).
        # DJ Shoulder World Pos = EnvPos(0,0,-3) + LocalShoulder(-0.2, 1.25, 0) -> (-0.2, 1.25, -3)
        dj_shoulder_pos = [-0.2, 1.25, -3]
        
        # Animate Target: Scratching motion
        scratch_offset = math.sin(t * 10) * 0.1
        target_hand = [deck_l_pos[0] + scratch_offset, deck_l_pos[1] + 0.1, deck_l_pos[2]]
        
        # Solve IK
        ik_res = anim_engine.execute_instruction(
            AgentAnimInstruction(
                op_code="IK_SOLVE",
                params={
                    "root_pos": dj_shoulder_pos,
                    "target_pos": target_hand,
                    "len_1": 0.45, # Arm
                    "len_2": 0.45  # Forearm
                },
                target_skeleton_id=dj_skel_id
            )
        )
        
        # MC LOGIC: Mic at Mouth
        # MC is at (1,0,1).
        # MC Shoulder World = (1+0.2, 1.25, 1) -> (1.2, 1.25, 1) approx (rotated?)
        # Let's just Bob the MC head
        head_bob = math.sin(t * 8) * 0.05
        
        frame_snapshot["dj_ik_l"] = ik_res
        frame_snapshot["mc_head_y"] = head_bob
        
        frames_data.append(frame_snapshot)

    # 7. EXPORT
    # We will export a JSON data block that index.html (grime_showcase.html) can read.
    # We define the HTML template inline here.
    
    scene_export = {
        "meshes": [],
        "lights": [l.model_dump() for l in scene.lights],
        "props": [],
        "frames": frames_data
    }
    
    # Export Meshes
    for mid, mesh in mesh_engine._store.items():
        # Triangulate
        flat_verts = [c for v in mesh.vertices for c in v]
        flat_indices = []
        for f in mesh.faces:
            if len(f)==3: flat_indices.extend(f)
            elif len(f)==4: flat_indices.extend([f[0],f[1],f[2], f[0],f[2],f[3]])
            
        if "chrome" in mid.lower() or "robot" in mid.lower():
             mat_props = mat_chrome.model_dump()
        elif "red" in mid.lower():
             mat_props = mat_wall_red.model_dump()
        else:
             mat_props = mat_floor.model_dump()

        scene_export["meshes"].append({
            "id": mid,
            "verts": flat_verts,
            "indices": flat_indices,
            "material": mat_props
        })

    # Export Prop Instances
    for node in scene.nodes:
        scene_export["props"].append({
            "mesh_id": node.mesh_id,
            "pos": [node.transform.position.x, node.transform.position.y, node.transform.position.z],
            "rot": [node.transform.rotation.x, node.transform.rotation.y, node.transform.rotation.z, node.transform.rotation.w],
            "scale": [node.transform.scale.x, node.transform.scale.y, node.transform.scale.z]
        })
        
    # WRITE HTML
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
<title>GRIME STUDIO</title>
<style>
  body {{ 
    margin: 0; 
    background: radial-gradient(circle at center, #222222 0%, #050505 100%); 
    overflow: hidden; 
  }}
</style>
<script type="importmap">
  {{
    "imports": {{
      "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
      "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
    }}
  }}
</script>
</head>
<body>
<div style="position: absolute; top: 20px; left: 20px; color: white; font-family: monospace;">
    <h1>GRIME STUDIO</h1>
    <p>DJ Selecta + MC Spit</p>
    <p>CAM: AUTOMATED DOLLY</p>
</div>
<script type="module">
    import * as THREE from 'three';
    
    const DATA = {json.dumps(scene_export)};
    
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x110505, 0.05); // Lighter Fog
    
    const camera = new THREE.PerspectiveCamera(50, window.innerWidth/window.innerHeight, 0.1, 100);
    camera.position.set(0, 2, 4);
    
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.useLegacyLights = false;
    renderer.toneMapping = THREE.ReinhardToneMapping;
    renderer.toneMappingExposure = 1.2; // Brighter exposure
    document.body.appendChild(renderer.domElement);
    
    // LIGHTS
    // Global Fill
    const hemiLight = new THREE.HemisphereLight( 0xffffff, 0x444444, 2.0 ); // Strong ambient
    scene.add( hemiLight );

    DATA.lights.forEach(l => {{
        const col = new THREE.Color(l.color.x, l.color.y, l.color.z);
        let light;
        // Boost intensity usage for PBR
        if(l.kind === 'spot') {{
            light = new THREE.SpotLight(col, l.intensity * 50.0); // Boosted
            light.distance = 50;
            light.angle = Math.PI/3;
            light.penumbra = 0.5;
        }} else {{
            light = new THREE.PointLight(col, l.intensity * 20.0, 30);
        }}
        if(l.position) light.position.set(l.position.x, l.position.y, l.position.z);
        scene.add(light);
    }});
    
    // MESH CACHE
    const meshCache = {{}};
    DATA.meshes.forEach(m => {{
        const geo = new THREE.BufferGeometry();
        geo.setAttribute('position', new THREE.Float32BufferAttribute(m.verts, 3));
        geo.setIndex(m.indices);
        geo.computeVertexNormals();
        
        const mat = new THREE.MeshStandardMaterial({{
            color: new THREE.Color(m.material.base_color[0], m.material.base_color[1], m.material.base_color[2]),
            metalness: m.material.metallic || 0,
            roughness: m.material.roughness || 0.5
        }});
        meshCache[m.id] = {{ geo, mat }};
    }});
    
    // SCENE BUILD
    const actors = [];
    DATA.props.forEach(p => {{
        if(meshCache[p.mesh_id]) {{
            const {{ geo, mat }} = meshCache[p.mesh_id];
            const mesh = new THREE.Mesh(geo, mat);
            mesh.position.set(p.pos[0], p.pos[1], p.pos[2]);
            mesh.quaternion.set(p.rot[0], p.rot[1], p.rot[2], p.rot[3]);
            mesh.scale.set(p.scale[0], p.scale[1], p.scale[2]);
            scene.add(mesh);
            
            // Hack to find actors based on mesh id
            if(p.mesh_id.includes("robot")) {{
                actors.push(mesh);
            }}
        }}
    }});
    
    // ANIMATION
    const frames = DATA.frames;
    const clock = new THREE.Clock();
    
    // Visualizing IK lines specifically
    const ikLineMat = new THREE.LineBasicMaterial({{ color: 0x00ff00 }});
    const ikGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0,0,0), new THREE.Vector3(0,1,0)]);
    const ikLine = new THREE.Line(ikGeo, ikLineMat);
    scene.add(ikLine);

    function animate() {{
        requestAnimationFrame(animate);
        
        const t = clock.getElapsedTime();
        const frameIdx = Math.floor((t * 30) % frames.length);
        const data = frames[frameIdx];
        
        // --- CINEMATIC CAMERA ---
        // Cycle every 8 seconds
        const camTime = t % 24;
        
        if(camTime < 8) {{
            // SHOT 1: Wide Dolly (Front) - Inside Room
            // Move from Left (-2) to Right (2) at height 1.5. Z=3 is inside room (Back wall is Z=4? No wait, Back wall is Z=-6, Front is Z=?? Cameras usually at pos Z)
            // Room is huge now (scale 14).
            // Let's keep Z roughly 3.
            const x = -2 + (camTime/8)*4;
            camera.position.set(x, 1.5, 3);
            camera.lookAt(0, 1, -2); // Look at center stage
        }} else if (camTime < 16) {{
            // SHOT 2: DJ Close Up
            // Orbitting the DJ
            const angle = (camTime - 8) * 0.5;
            camera.position.set(Math.sin(angle)*2, 1.8, -3 + Math.cos(angle)*2);
            camera.lookAt(0, 1.2, -3); // Look at DJ Head
        }} else {{
            // SHOT 3: MC Low Angle
            // Looking up at MC
            camera.position.set(1 + Math.sin(t)*0.2, 0.5, 2);
            camera.lookAt(1, 1.5, 1); // Look at MC Head
        }}

        if(data && actors[1]) {{
            actors[1].position.y = data.mc_head_y;
            if(data.dj_ik_l) {{
                const shoulder = new THREE.Vector3(-0.2, 1.25, -3);
                const elbow = new THREE.Vector3(data.dj_ik_l.elbow_pos[0], data.dj_ik_l.elbow_pos[1], data.dj_ik_l.elbow_pos[2]);
                ikGeo.setFromPoints([shoulder, elbow]);
            }}
        }} 
        renderer.render(scene, camera);
    }}
    animate();
</script>
</body>
</html>
    """
    
    with open("grime_showcase.html", "w") as f:
        f.write(html_content)
    print("✅ GENERATED: grime_showcase.html")

if __name__ == "__main__":
    run_show()
