"""
THE DIRECTOR: FORTNITE EDITION
------------------------------
Orchestrates the Stylized High-Fidelity Showcase.
"""
import json
import math
import random
import sys
import os
sys.path.append(os.getcwd())
from typing import List, Dict

# Engines
from engines.mesh_kernel.service import MeshService
from engines.stage_kernel.service import StageService
from engines.stage_kernel.schemas import AgentStageInstruction, PropDefinition, PropType
from engines.animation_kernel.service import AnimationService
from engines.material_kernel.service import MaterialService
from engines.material_kernel.schemas import AgentMaterialInstruction

# Generators
from engines.showcase.human_nature.generators import gen_fortnite, gen_nature
from engines.showcase.human_nature.animator import evaluate_walk_cycle

def run_show():
    print("🎮 ACTION: Fortnite Sequence Started...")
    
    # 1. INIT ENGINES
    mesh_engine = MeshService()
    mat_engine = MaterialService()
    anim_engine = AnimationService()
    stage_engine = StageService()
    scene = stage_engine.create_empty_scene()
    sid = scene.id
    
    # 2. GENERATE ASSETS
    print("🧬 BIO LAB: Extruding Avatar...")
    skel_id, avatar_mesh_id = gen_fortnite.generate_fortnite_avatar(mesh_engine, anim_engine)
    
    print("⛰️ TERRAFORM: Generating Landscape...")
    terrain_id = gen_nature.generate_terrain(mesh_engine, size=100.0, resolution=64)
    grass_id = gen_nature.generate_grass_patch(mesh_engine, density=40, radius=2.0)
    
    # Register Props
    stage_engine._prop_library["prop_avatar"] = PropDefinition(id="prop_avatar", name="Avatar", kind=PropType.STATIC_MESH, mesh_asset_id=avatar_mesh_id)
    stage_engine._prop_library["prop_terrain"] = PropDefinition(id="prop_terrain", name="Terrain", kind=PropType.STATIC_MESH, mesh_asset_id=terrain_id)
    stage_engine._prop_library["prop_grass"] = PropDefinition(id="prop_grass", name="Grass", kind=PropType.STATIC_MESH, mesh_asset_id=grass_id)

    # 3. MATERIALS (TOON)
    # We define instructions, but export logic handles shader.
    # We use these objects to store colors.
    mat_skin = mat_engine.execute_instruction(AgentMaterialInstruction(op_code="CREATE", params={"name": "SkinToon", "base_color": [0.9, 0.7, 0.6, 1], "roughness": 0.0}), target_mesh=None)
    mat_suit = mat_engine.execute_instruction(AgentMaterialInstruction(op_code="CREATE", params={"name": "SuitToon", "base_color": [0.1, 0.2, 0.7, 1], "roughness": 0.0}), target_mesh=None) # Bright Blue Suit
    mat_grass = mat_engine.execute_instruction(AgentMaterialInstruction(op_code="CREATE", params={"name": "GrassToon", "base_color": [0.3, 0.8, 0.1, 1], "roughness": 1.0}), target_mesh=None)
    mat_terrain = mat_engine.execute_instruction(AgentMaterialInstruction(op_code="CREATE", params={"name": "TerrainToon", "base_color": [0.2, 0.5, 0.1, 1], "roughness": 1.0}), target_mesh=None) # Base Green
    
    # 4. SET CONSTRUCTION
    # Spawn Props
    stage_engine.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "prop_terrain", "position": [0, -1, 0]}, target_scene_id=sid))
    
    stage_engine.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "prop_avatar", "position": [0,0,0]}, target_scene_id=sid))
    
    # Grass Clumps
    for _ in range(100):
        gx = (random.random() - 0.5) * 80
        gz = (random.random() - 0.5) * 80
        gr = random.random() * math.pi * 2
        stage_engine.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "prop_grass", "position": [gx, -1, gz], "rotation": [0, math.sin(gr), 0, math.cos(gr)]}, target_scene_id=sid))
        
    # 5. LIGHTING
    # Bright Sun for Toon
    stage_engine.execute_instruction(AgentStageInstruction(op_code="SET_LIGHT", params={"type": "DIRECTIONAL", "color": [1.0, 0.98, 0.9], "intensity": 1.5, "position": [50, 50, 50]}, target_scene_id=sid))

    # 6. ANIMATION
    print("🎥 ACTION: Recording Mocap...")
    frames_data = []
    total_frames = 120
    
    # Export Skeleton Structure for Three.js
    skel = anim_engine._skeletons[skel_id]
    # We need ordered list of bones matching indices
    # AnimEngine stores list.
    skeleton_export = []
    for b in skel.bones:
        p_idx = -1
        if b.parent_id:
            # Find index of parent
            for i, pb in enumerate(skel.bones):
                if pb.id == b.parent_id:
                    p_idx = i
                    break
        skeleton_export.append({
            "name": b.id,
            "parent": p_idx,
            "pos": b.head_pos, # Bind Pose (Absolute world in our schema? No, Schema says "Local relative to parent" but implementation used absolute logic? Wait.)
            # Schema says: head_pos [x,y,z].
            # Implementation of AUTO_RIG used ABSOLUTE coords in comments.
            # But Three.js needs RELATIVE local matrix usually (or we allow it to calc inverses).
            # If we pass `pos` and `rot` to Bone, it assumes local to parent.
            # We implemented `_solve_fk` in last director because of this confusion.
            # Correction: Our `AnimationService` creates Bone objects with `head_pos` = ABSOLUTE world coords of joints in T-Pose.
            # We must convert to RELATIVE for Three.js Bone hierarchy construction?
            # Or use Three.js helper to attach.
            # Let's simple export Absolute bind pose, and use a Client-side helper to compute relative offsets OR just flatten hierarchy in Three.js?
            # No, hierarchy is needed for rotation propagation.
            
            # Converter:
            # RelPos = ChildAbs - ParentAbs. Apply InverseParentRot? 
            # In T-Pose, Rotations are identity.
            # So RelPos = ChildAbs - ParentAbs.
            "abs_pos": b.head_pos, 
            "rot": [0,0,0,1]
        })
        
    # Animation Frames: Just Bone Rotations (Local)
    # The Animator `evaluate_walk_cycle` returns Local Rotations.
    # This matches Three.js expectation if bones are hierarchical.
    for f in range(total_frames):
        t = f / 30.0
        pose = evaluate_walk_cycle(t) # {bone_id: quat}
        
        # We need to map bone_id to bone_index for efficient array
        frame_rotations = [] 
        for b in skel.bones:
            q = pose.get(b.id, [0,0,0,1])
            frame_rotations.append(q)
            
        frames_data.append(frame_rotations)

    # 7. EXPORT
    scene_export = {
        "meshes": [],
        "lights": [l.model_dump() for l in scene.lights],
        "props": [],
        "frames": frames_data,
        "skeleton": skeleton_export,
        "skinning": True
    }
    
    # Export Meshes
    for mid, mesh in mesh_engine._store.items():
        # Vertex Colors (for Toon?) or just Material.
        # Skin Weights
        skin_indices = []
        skin_weights = []
        
        if mesh.skin_weights:
            # Convert dict {bone_id: w} to 4 indices/weights
            bone_id_to_idx = {b.id: i for i, b in enumerate(skel.bones)}
            
            for sw in mesh.skin_weights:
                # Top 4 interactions
                # Sort by weight desc
                sorted_w = sorted(sw.items(), key=lambda item: item[1], reverse=True)
                
                # Fill 4 slots
                indices = [0,0,0,0]
                weights = [0,0,0,0]
                
                for i in range(min(4, len(sorted_w))):
                    bid, w = sorted_w[i]
                    if bid in bone_id_to_idx:
                        indices[i] = bone_id_to_idx[bid]
                        weights[i] = w
                        
                skin_indices.extend(indices)
                skin_weights.extend(weights)
        
        # Flatten Geom
        flat_verts = [c for v in mesh.vertices for c in v]
        flat_indices = []
        for f in mesh.faces:
             if len(f)==3: flat_indices.extend(f)
             elif len(f)==4: flat_indices.extend([f[0],f[1],f[2], f[0],f[2],f[3]])
             
        # Material
        mat_color = [1,1,1]
        if mid == avatar_mesh_id: mat_color = mat_suit.base_color
        elif mid == terrain_id: mat_color = mat_terrain.base_color
        elif "grass" in mid: mat_color = mat_grass.base_color
        
        scene_export["meshes"].append({
            "id": mid,
            "verts": flat_verts,
            "indices": flat_indices,
            "uvs": [c for pair in mesh.uvs for c in pair] if mesh.uvs else [],
            "skinIndices": skin_indices,
            "skinWeights": skin_weights,
            "color": mat_color
        })
        
    # Export Props
    for node in scene.nodes:
         scene_export["props"].append({
            "id": node.id,
            "mesh_id": node.mesh_id,
            "pos": [node.transform.position.x, node.transform.position.y, node.transform.position.z],
            "rot": [node.transform.rotation.x, node.transform.rotation.y, node.transform.rotation.z, node.transform.rotation.w],
            "scale": [node.transform.scale.x, node.transform.scale.y, node.transform.scale.z]
         })

    # HTML
    html = create_html(scene_export)
    with open("fortnite_showcase.html", "w") as f:
        f.write(html)
    print("✅ GENERATED: fortnite_showcase.html")

def create_html(data):
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>FORTNITE SHOWCASE</title>
    <style>
        body {{ margin: 0; overflow: hidden; background: linear-gradient(to bottom, #4facfe 0%, #00f2fe 100%); }}
        canvas {{ display: block; }}
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
    <script type="module">
        import * as THREE from 'three';
        import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
        import {{ EffectComposer }} from 'three/addons/postprocessing/EffectComposer.js';
        import {{ RenderPass }} from 'three/addons/postprocessing/RenderPass.js';
        import {{ UnrealBloomPass }} from 'three/addons/postprocessing/UnrealBloomPass.js';

        const DATA = {json.dumps(data)};
        
        const scene = new THREE.Scene();
        scene.fog = new THREE.Fog(0x00f2fe, 20, 100);
        
        const camera = new THREE.PerspectiveCamera(60, window.innerWidth/window.innerHeight, 0.1, 200);
        camera.position.set(0, 3, 6);
        
        const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        document.body.appendChild(renderer.domElement);
        
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.target.set(0, 1.5, 0); // Targeted at chest
        controls.enableDamping = true;
        controls.maxPolarAngle = Math.PI / 2 - 0.1; // Don't go below ground
        
        // --- PROCEDURAL TEXTURES (CANVAS) ---
        function createSkinTexture() {{
            const canvas = document.createElement('canvas');
            canvas.width = 512; canvas.height = 512;
            const ctx = canvas.getContext('2d');
            
            // Base Skin
            ctx.fillStyle = "#e0ac69";
            ctx.fillRect(0,0,512,512);
            
            // Noise?
            
            // Face Details (Mapped via Cylindrical Projection)
            // U=0.5 is Front face. V=0.8-0.9 is Head.
            // Eyes
            const cx = 256; 
            const cy = 50; // High up (v ~ 0.9)
            
            // Eye Left
            ctx.fillStyle = "white";
            ctx.beginPath(); ctx.ellipse(cx - 30, cy, 15, 10, 0, 0, Math.PI*2); ctx.fill();
            ctx.fillStyle = "#3366cc";
            ctx.beginPath(); ctx.arc(cx - 30, cy, 6, 0, Math.PI*2); ctx.fill();
            
            // Eye Right
            ctx.fillStyle = "white";
            ctx.beginPath(); ctx.ellipse(cx + 30, cy, 15, 10, 0, 0, Math.PI*2); ctx.fill();
            ctx.fillStyle = "#3366cc";
            ctx.beginPath(); ctx.arc(cx + 30, cy, 6, 0, Math.PI*2); ctx.fill();
            
            // Mouth
            ctx.strokeStyle = "#a05a2c";
            ctx.lineWidth = 3;
            ctx.beginPath(); ctx.arc(cx, cy+30, 15, 0, Math.PI, false); ctx.stroke();
            
            return new THREE.CanvasTexture(canvas);
        }}
        
        function createSuitTexture() {{
            const canvas = document.createElement('canvas');
            canvas.width = 512; canvas.height = 512;
            const ctx = canvas.getContext('2d');
            
            // Base Navy
            ctx.fillStyle = "#1a1a40";
            ctx.fillRect(0,0,512,512);
            
            // Fabric Noise
            for(let i=0; i<5000; i++) {{
                ctx.fillStyle = Math.random() > 0.5 ? "#202050" : "#151535";
                ctx.fillRect(Math.random()*512, Math.random()*512, 2, 2);
            }}
            
            // Buttons/Lapels (Front Center U=0.5)
            // Torso is V=0.5 to 0.7 approx
            ctx.fillStyle = "black";
            const bx = 256;
            ctx.beginPath(); ctx.arc(bx, 250, 5, 0, Math.PI*2); ctx.fill();
            ctx.beginPath(); ctx.arc(bx, 280, 5, 0, Math.PI*2); ctx.fill();
            ctx.beginPath(); ctx.arc(bx, 310, 5, 0, Math.PI*2); ctx.fill();
            
            // Tie (Red Strip)
            ctx.fillStyle = "#aa2020";
            ctx.fillRect(bx-10, 200, 20, 150);
            
            return new THREE.CanvasTexture(canvas);
        }}
        
        const skinTex = createSkinTexture();
        const suitTex = createSuitTexture();
        
        // TOON GRADIENT MAP
        const gradientMap = new THREE.DataTexture(
            new Uint8Array([20, 100, 255]), 3, 1, 
            THREE.RedFormat
        );
        gradientMap.minFilter = THREE.NearestFilter;
        gradientMap.magFilter = THREE.NearestFilter;
        gradientMap.needsUpdate = true;
        
        // LIGHTS
        const ambient = new THREE.AmbientLight(0x404040, 0.5); 
        scene.add(ambient);
        
        const sun = new THREE.DirectionalLight(0xffffff, 1.5);
        sun.position.set(20, 50, 20);
        sun.castShadow = true;
        sun.shadow.mapSize.width = 2048;
        sun.shadow.mapSize.height = 2048;
        scene.add(sun);
        
        // FX COMPOSER
        const composer = new EffectComposer(renderer);
        const renderPass = new RenderPass(scene, camera);
        composer.addPass(renderPass);
        
        const bloomPass = new UnrealBloomPass( new THREE.Vector2( window.innerWidth, window.innerHeight ), 1.5, 0.4, 0.85 );
        bloomPass.threshold = 0.5;
        bloomPass.strength = 0.4;
        bloomPass.radius = 0.1;
        composer.addPass(bloomPass);
        
        // MESH CACHE
        const meshCache = {{}};
        DATA.meshes.forEach(m => {{
            const geo = new THREE.BufferGeometry();
            geo.setAttribute('position', new THREE.Float32BufferAttribute(m.verts, 3));
            geo.setIndex(m.indices);
            
            if(m.uvs && m.uvs.length > 0) {{
                geo.setAttribute('uv', new THREE.Float32BufferAttribute(m.uvs, 2));
            }}
            
            if(m.skinIndices && m.skinIndices.length > 0) {{
                geo.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(m.skinIndices, 4));
                geo.setAttribute('skinWeight', new THREE.Float32BufferAttribute(m.skinWeights, 4));
            }}
            
            geo.computeVertexNormals();
            
            // MATERIAL SELECTION
            // If Avatar Id -> Apply Texture Map
            // We need to know which material to use.
            // Heuristic: If ID contains "avatar" -> Use Suit Texture? 
            let map = null;
            if(m.id.includes("avatar")) map = suitTex; // Apply Suit to Body
            // Wait, we have ONE mesh for Head + Body + Legs.
            // UVs map Head to V > 0.8...
            // So we need a COMPOSITE texture? Or just use one texture for whole body?
            // Let's create `createAvatarTexture` that draws EVERYTHING.
            
            const col = new THREE.Color(m.color[0], m.color[1], m.color[2]);
            const mat = new THREE.MeshToonMaterial({{
                color: (map ? 0xffffff : col), // If map, use white base
                map: map,
                gradientMap: gradientMap,
                side: THREE.DoubleSide
            }});
            
            meshCache[m.id] = {{ geo, mat, skinned: (m.skinIndices.length > 0) }};
        }});
        
        // SKELETON SETUP
        const bones = [];
        if(DATA.skeleton) {{
            DATA.skeleton.forEach((bData, i) => {{
                const bone = new THREE.Bone();
                bone.name = bData.name;
                bones.push(bone);
            }});
            
            DATA.skeleton.forEach((bData, i) => {{
                if(bData.parent !== -1) {{
                    bones[bData.parent].add(bones[i]);
                    const pData = DATA.skeleton[bData.parent];
                    const relX = bData.abs_pos[0] - pData.abs_pos[0];
                    const relY = bData.abs_pos[1] - pData.abs_pos[1];
                    const relZ = bData.abs_pos[2] - pData.abs_pos[2];
                    bones[i].position.set(relX, relY, relZ);
                }} else {{
                    bones[i].position.set(bData.abs_pos[0], bData.abs_pos[1], bData.abs_pos[2]);
                }}
            }});
        }}
        const skeleton = new THREE.Skeleton(bones);
        
        // PROPS
        const mixers = [];
        DATA.props.forEach(p => {{
            if(meshCache[p.mesh_id]) {{
                const {{ geo, mat, skinned }} = meshCache[p.mesh_id];
                let mesh;
                
                if(skinned) {{
                    mesh = new THREE.SkinnedMesh(geo, mat);
                    mesh.add(bones[0]); 
                    mesh.bind(skeleton);
                }} else {{
                    mesh = new THREE.Mesh(geo, mat);
                }}
                
                mesh.position.set(p.pos[0], p.pos[1], p.pos[2]);
                mesh.quaternion.set(p.rot[0], p.rot[1], p.rot[2], p.rot[3]);
                mesh.scale.set(p.scale[0], p.scale[1], p.scale[2]);
                
                mesh.castShadow = true;
                mesh.receiveShadow = true;
                
                scene.add(mesh);
            }}
        }});
        
        // ANIMATION LOOP
        const clock = new THREE.Clock();
        const frames = DATA.frames;
        
        function animate() {{
            requestAnimationFrame(animate);
            controls.update();
            const t = clock.getElapsedTime();
            
            const frameIdx = Math.floor((t * 30) % frames.length);
            const pose = frames[frameIdx]; 
            
            if(pose && bones.length > 0) {{
                pose.forEach((q, i) => {{
                    if(bones[i]) {{
                        bones[i].quaternion.set(q[0], q[1], q[2], q[3]);
                    }}
                }});
            }}
            
            composer.render();
        }}
        animate();
    </script>
</body>
</html>
    """
    
if __name__ == "__main__":
    run_show()
