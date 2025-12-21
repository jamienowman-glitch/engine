"""
FULL GAS SHOWCASE GENERATOR
---------------------------
Orchestrates Mesh, Material, Animation, and Stage engines to produce
a high-fidelity visual demonstration.

Output: showcase.html
"""
import json
import math
from typing import Dict, List, Any

# Engine Imports
from engines.mesh_kernel.service import MeshService
from engines.mesh_kernel.schemas import AgentMeshInstruction, MeshObject
from engines.material_kernel.service import MaterialService
from engines.material_kernel.schemas import AgentMaterialInstruction
from engines.animation_kernel.service import AnimationService
from engines.animation_kernel.schemas import AgentAnimInstruction
from engines.stage_kernel.service import StageService
from engines.stage_kernel.schemas import AgentStageInstruction

def generate_showcase():
    print("🚀 IGNITION: Starting Full Gas Showcase Generation...")
    
    # 1. Initialize Engines
    mesh_engine = MeshService()
    mat_engine = MaterialService()
    anim_engine = AnimationService()
    stage_engine = StageService()
    
    scene_data = {
        "meshes": [],
        "lights": [],
        "props": [],
        "animation": {}
    }

    # --- PHASE 1: THE CLAY (Mesh) ---
    print("🎨 MESH: Sculpting Cyberhead...")
    # Start with a Cube (Primitive)
    base_mesh = mesh_engine.execute_instruction(
        AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "CUBE", "size": 1.0})
    )
    
    # Subdivide x2 to get a smooth sphere-like topology (Catmull-Clark)
    # Cube (6 faces) -> L1 (24) -> L2 (96) -> L3 (384)
    subd_mesh = mesh_engine.execute_instruction(
        AgentMeshInstruction(op_code="SUBDIVIDE", params={"iterations": 2}, target_id=base_mesh.id)
    )
    
    # Sculpting: Deform it to look interesting (Alien Head shape)
    # Inflate top (Brain)
    mesh_engine.execute_instruction(
        AgentMeshInstruction(
            op_code="SCULPT", 
            params={
                "brush": "INFLATE", 
                "center": {"x": 0, "y": 0.5, "z": 0}, 
                "radius": 0.8, 
                "strength": 0.5
            },
            target_id=subd_mesh.id
        )
    )
    # Move Chindown
    mesh_engine.execute_instruction(
        AgentMeshInstruction(
            op_code="SCULPT", 
            params={
                "brush": "MOVE", 
                "center": {"x": 0, "y": -0.5, "z": 0}, 
                "radius": 0.5, 
                "strength": 0.3 # Pull down
            },
            target_id=subd_mesh.id
        )
    )

    # --- PHASE 2: THE PAINT (Material) ---
    print("🖌️ MATERIAL: Applying Liquid Gold...")
    # Create Custom Material
    gold_mat_instr = AgentMaterialInstruction(
        op_code="CREATE",
        params={
            "name": "CyberGold",
            "base_color": [1.0, 0.85, 0.5, 1.0],
            "metallic": 1.0,
            "roughness": 0.15
        }
    )
    gold_mat = mat_engine.execute_instruction(gold_mat_instr, target_mesh=None)
    
    # Apply to Mesh
    mat_engine.execute_instruction(
        AgentMaterialInstruction(
            op_code="APPLY_PRESET",
            params={"material_id": gold_mat.id},
            target_id=subd_mesh.id
        ),
        target_mesh=subd_mesh
    )

    # --- PHASE 3: THE BONES (Animation) ---
    print("💀 ANIMATION: Rigging & animating...")
    # Auto Rig
    skeleton = anim_engine.execute_instruction(
        AgentAnimInstruction(op_code="AUTO_RIG", params={})
    )
    
    # Generate Animation Data (Procedural Float/Head Turn)
    # We will sample 60 frames
    anim_track = []
    for f in range(60):
        t = f / 60.0
        pose = anim_engine.execute_instruction(
            AgentAnimInstruction(
                op_code="PLAY_ANIM",
                params={"clip_name": "WALK", "time": t}, # Reusing walk cycle math for visual test
                target_skeleton_id=skeleton.id
            )
        )
        # Store frame data
        anim_track.append(pose)

    scene_data["animation"] = anim_track

    # --- PHASE 4: THE STAGE (World) ---
    print("🌍 STAGE: Constructing the Room...")
    stage_scene = stage_engine.create_empty_scene()
    
    # Lighting: Studio Setup (Bright & Clean)
    # Key Light (Warm)
    stage_engine.execute_instruction(
        AgentStageInstruction(
            op_code="SET_LIGHT",
            params={"type": "POINT", "color": [1.0, 0.95, 0.8], "intensity": 8.0, "position": [4, 5, 4]},
            target_scene_id=stage_scene.id
        )
    )
    # Fill Light (Cool)
    stage_engine.execute_instruction(
        AgentStageInstruction(
            op_code="SET_LIGHT",
            params={"type": "POINT", "color": [0.8, 0.9, 1.0], "intensity": 4.0, "position": [-4, 3, 2]},
            target_scene_id=stage_scene.id
        )
    )
    # Rim Light (Bright Edge)
    stage_engine.execute_instruction(
        AgentStageInstruction(
            op_code="SET_LIGHT",
            params={"type": "SPOT", "color": [1.0, 1.0, 1.0], "intensity": 10.0, "position": [0, 5, -5]},
            target_scene_id=stage_scene.id
        )
    )

    # Props: Building a "Little Room" using Floor Tiles
    # Floor
    stage_engine.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "prop_floor_tile", "position": [0, -2, 0]}, target_scene_id=stage_scene.id))
    # Back Wall (Rotate 90 deg X) -> Quat [0.707, 0, 0, 0.707]
    stage_engine.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "prop_floor_tile", "position": [0, 3, -5], "rotation": [0.707, 0, 0, 0.707]}, target_scene_id=stage_scene.id))
    # Left Wall (Rotate 90 deg Z) -> Quat [0, 0, 0.707, 0.707]
    stage_engine.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "prop_floor_tile", "position": [-5, 3, 0], "rotation": [0, 0, -0.707, 0.707]}, target_scene_id=stage_scene.id))
    # Right Wall
    stage_engine.execute_instruction(AgentStageInstruction(op_code="SPAWN_PROP", params={"prop_id": "prop_floor_tile", "position": [5, 3, 0], "rotation": [0, 0, 0.707, 0.707]}, target_scene_id=stage_scene.id))
    
    # --- EXPORT TO HTML ---
    print("📦 EXPORTING: showcase.html")
    
    # Prepare Mesh Data for Three.js
    flat_verts = [c for v in subd_mesh.vertices for c in v]
    flat_indices = []
    for f in subd_mesh.faces:
        if len(f) == 4:
            flat_indices.extend([f[0], f[1], f[2], f[0], f[2], f[3]])
        elif len(f) == 3:
            flat_indices.extend(f)

    scene_data["meshes"].append({
        "verts": flat_verts,
        "indices": flat_indices,
        "material": gold_mat.model_dump()
    })
    
    scene_data["lights"] = [l.model_dump() for l in stage_scene.lights]
    scene_data["props"] = [{"name": n.name, "pos": [n.transform.position.x, n.transform.position.y, n.transform.position.z], "rot": [n.transform.rotation.x, n.transform.rotation.y, n.transform.rotation.z, n.transform.rotation.w], "scale": [n.transform.scale.x, n.transform.scale.y, n.transform.scale.z]} for n in stage_scene.nodes]

    # Generate HTML
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>NORTHSTAR ENGINES: STUDIO SHOWCASE</title>
    <style>body {{ margin: 0; background: radial-gradient(circle at center, #333333 0%, #111111 100%); color: #fff; font-family: sans-serif; overflow: hidden; }}</style>
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
    <div style="position:absolute; top:20px; left:20px; z-index:100; pointer-events:none;">
        <h1>ENGINE SHOWCASE: "GLORIOUS GOLD"</h1>
        <p style="opacity:0.7;">
        <b>Mesh:</b> Catmull-Clark SubD (L2) + Sculpt<br>
        <b>Material:</b> PBR "CyberGold"<br>
        <b>Stage:</b> Studio Room (Procedural Instancing)<br>
        <b>Lighting:</b> 3-Point Setup
        </p>
    </div>
    <script type="module">
        import * as THREE from 'three';
        import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';

        // --- DATA INJECTION ---
        const SCENE_DATA = {json.dumps(scene_data)};
        
        // --- SETUP ---
        const scene = new THREE.Scene();
        // Remove fog for studio look, or keep it subtle
        // scene.fog = new THREE.FogExp2(0x111111, 0.02);
        
        const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.set(0, 1, 5);

        const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.outputColorSpace = THREE.SRGBColorSpace;
        renderer.shadowMap.enabled = true;
        document.body.appendChild(renderer.domElement);

        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.autoRotate = true;
        controls.autoRotateSpeed = 1.0;
        controls.target.set(0, 0, 0);

        // --- STAGE: LIGHTS ---
        SCENE_DATA.lights.forEach(l => {{
            const color = new THREE.Color(l.color.x, l.color.y, l.color.z);
            let light;
            if (l.kind === 'directional') {{
                light = new THREE.DirectionalLight(color, l.intensity);
                light.position.set(l.position.x, l.position.y, l.position.z);
            }} else if (l.kind === 'spot') {{
                light = new THREE.SpotLight(color, l.intensity);
                light.position.set(l.position.x, l.position.y, l.position.z);
                light.angle = Math.PI / 4;
                light.penumbra = 0.5;
            }} else {{
                light = new THREE.PointLight(color, l.intensity);
                light.position.set(l.position.x, l.position.y, l.position.z);
            }}
            scene.add(light);
            // Helpers
            // const helper = new THREE.PointLightHelper(light, 0.2);
            // scene.add(helper);
        }});
        
        scene.add(new THREE.AmbientLight(0x404040, 2.0)); // Brighter Ambient

        // --- MESH: THE AVATAR ---
        const meshData = SCENE_DATA.meshes[0];
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.Float32BufferAttribute(meshData.verts, 3));
        geometry.setIndex(meshData.indices);
        geometry.computeVertexNormals();

        const matData = meshData.material;
        const material = new THREE.MeshStandardMaterial({{
            color: new THREE.Color(matData.base_color[0], matData.base_color[1], matData.base_color[2]),
            metalness: matData.metallic,
            roughness: matData.roughness,
            side: THREE.DoubleSide
        }});

        const avatar = new THREE.Mesh(geometry, material);
        scene.add(avatar);

        // --- STAGE: PROPS (The Room) ---
        const propGeo = new THREE.PlaneGeometry(1, 1);
        const propMat = new THREE.MeshStandardMaterial({{ color: 0x888888, roughness: 0.8 }});
        
        SCENE_DATA.props.forEach(p => {{
            const mesh = new THREE.Mesh(propGeo, propMat);
            mesh.position.set(p.pos[0], p.pos[1], p.pos[2]);
            mesh.quaternion.set(p.rot[0], p.rot[1], p.rot[2], p.rot[3]);
            // Apply scale explicitly because we are using PlaneGeometry
            // Our service defaults props [5,10,5] for buildings but for floor tiles?
            // Let's assume tiles are huge panels (10x10)
            mesh.scale.set(10, 10, 1); 
            
            scene.add(mesh);
        }});

        // --- ANIMATION LOOP ---
        const clock = new THREE.Clock();
        const animData = SCENE_DATA.animation;
        const totalFrames = animData.length;

        function animate() {{
            requestAnimationFrame(animate);
            controls.update();
            
            const t = clock.getElapsedTime();
            const frameIdx = Math.floor((t % 1.0) * 60) % totalFrames;
            const pose = animData[frameIdx];
            
            if (pose && pose.root) {{
                avatar.position.y = Math.sin(t) * 0.1;
                avatar.rotation.y = Math.sin(t * 0.5) * 0.2;
            }}

            renderer.render(scene, camera);
        }}
        animate();

        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }});
    </script>
</body>
</html>
    """
    
    with open("showcase.html", "w") as f:
        f.write(html)
    
    print("✅ GENERATION COMPLETE. Open 'showcase.html' in your browser.")

if __name__ == "__main__":
    generate_showcase()
