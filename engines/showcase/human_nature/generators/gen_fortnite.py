"""
GENERATOR: FORTNITE CHARACTER
-----------------------------
Unified Mesh Generation (Box Modeling + Subdivision).
"""
from typing import Tuple, Dict
import math

from engines.mesh_kernel.service import MeshService
from engines.mesh_kernel.schemas import AgentMeshInstruction
from engines.mesh_kernel.ops.builder_ops import MeshBuilder
from engines.animation_kernel.service import AnimationService

def generate_fortnite_avatar(mesh_engine: MeshService, anim_engine: AnimationService) -> Tuple[str, str]:
    """
    Generates a single-mesh stylized avatar.
    Returns (skeleton_id, mesh_id).
    """
    # 1. Start with Torso Block (0.5 x 0.6 x 0.3)
    torso = mesh_engine.execute_instruction(AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "CUBE", "size": 1.0}))
    torso.id = "avatar_base"
    mesh_engine._store[torso.id] = torso
    
    # Scale to Torso logic
    # We want 0.5 width, 0.6 height, 0.25 depth
    # Center is 0,0,0.
    builder = MeshBuilder(torso)
    
    # Init Scale
    sx, sy, sz = 0.5, 0.6, 0.25
    for idx, v in enumerate(torso.vertices):
        torso.vertices[idx] = [v[0]*sx, v[1]*sy, v[2]*sz]
        
    # Move up so feet will be on ground
    # Legs approx 0.9m. Torso center currently 0.0.
    # We want Torso Center at 0.9 + 0.3 = 1.2?
    # Actually let's model relative then move.
    
    # 2. Extrude NECK & HEAD (Top Face)
    # Find Top (Normal +Y)
    top_idx = builder.select_face_by_normal([0, 1, 0])
    
    # Extrude Neck
    builder.extrude_face(top_idx, 0.1) # Up
    builder.scale_face(top_idx, 0.6) # Narrow neck
    
    # Extrude Head Base
    builder.extrude_face(top_idx, 0.1) 
    builder.scale_face(top_idx, 1.5) # Widen to Head
    
    # Extrude Head Main
    builder.extrude_face(top_idx, 0.25) # Main head volume
    
    # 3. Extrude LEGS (Bottom Face)
    # This is tricky with single box. We need *two* legs.
    # Standard box has 1 bottom face.
    # We should have started with a split box (Left/Right)?
    # Or we select "Bottom Left" quadrant? Standard cube has 1 face per side.
    # To get two legs, we can Extrude Hips Down, then Subdivide/Split?
    # Or better: Start with TWO cubes for hips and merge? No, unified mesh.
    
    # Box Modeling Trick: Extrude "Pelvis" down, then widen?
    # No, we need topology for gap.
    # Quick fix: Extrude ONE block for Legs, then scale it X-wide to look like skirt/pants?
    # User wants Fortnite.
    # Correct topology: Subdivide the Mesh *before* extruding legs.
    # If we run linear subdivision (split quads) once, we get 4 faces on bottom.
    # Then we can extrude the left and right ones.
    
    # Force Subdivide (Linear? No, CC smooths).
    # MeshService only has CC. 
    # Let's perform a "Knife Cut" logic manually or just use CC with iter=1, creates geometry.
    mesh_engine.execute_instruction(AgentMeshInstruction(op_code="SUBDIVIDE", params={"iterations": 1}, target_id=torso.id))
    # CAUTION: CC smooths the shape into a blob. We might lose our crisp torso.
    # But for "Stylized", blob is good.
    # After 1 iteration, a Cube becomes 6x4 = 24 quads.
    # Each original face becomes 4 faces.
    
    # Re-wrap builder (mesh changed)
    builder = MeshBuilder(mesh_engine._store[torso.id])
    
    # Now Bottom Face (-Y) is composed of 4 faces.
    # We want Bottom-Left and Bottom-Right.
    # Normals are all -Y.
    # Position distinguishes them.
    # Center X=0. Resulting faces: (-X, -Z), (+X, -Z), (-X, +Z), (+X, +Z).
    # We want the ones with -X (Left Leg) and +X (Right Leg).
    # And maybe merge the Z's?
    
    # Let's find all bottom faces.
    bottom_faces = []
    for f_idx, face in enumerate(torso.faces):
        ctr = builder.get_face_center(f_idx)
        # Check normal manually or check Y level?
        # Y is lowest point.
        # But after CC, shape is sphere-like.
        # Let's check normal.
        ns = _compute_normal(torso, face)
        if ns[1] < -0.9:
            bottom_faces.append(f_idx)
            
    # Sort by X?
    # We expect 4 faces (CC on bottom quad).
    # Front-Left, Front-Right, Back-Left, Back-Right.
    # We want to extrude (FL + BL) as Left Leg, (FR + BR) as Right Leg.
    # But `extrude_face` works on single face.
    # We can extrude them individually and try to keep them together?
    # Or just extrude the 4 corners as 4 spider legs?
    # For simplicity in this script: Extrude 4 legs. It'll look alien but cool style?
    # No, Human.
    # Let's just pick Front-Left and Front-Right?
    # Or just extrude ONE central leg (peg leg) just to prove unified mesh?
    # No, user wants quality.
    
    # Strategy: Extrude individual faces.
    left_leg_faces = [f for f in bottom_faces if builder.get_face_center(f)[0] < 0]
    right_leg_faces = [f for f in bottom_faces if builder.get_face_center(f)[0] > 0]
    
    # Extrude Left Leg (iteratively for knee)
    # We extrude EACH face in left_leg_faces.
    for f in left_leg_faces:
        nid = builder.extrude_face(f, 0.4) # Thigh
        nid = builder.extrude_face(nid, 0.4) # Calf
        
    for f in right_leg_faces:
        nid = builder.extrude_face(f, 0.4)
        nid = builder.extrude_face(nid, 0.4)
        
    # 4. ARMS (Side Faces)
    # Normal +X (Right), -X (Left).
    # After CC, side faces are valid.
    left_arm_faces = []
    right_arm_faces = []
    
    # We only want TOP side faces (Shoulders), not bottom (ribs).
    for f_idx, face in enumerate(torso.faces):
        ctr = builder.get_face_center(f_idx)
        ns = _compute_normal(torso, face)
        if ns[0] < -0.8 and ctr[1] > 0: # Left, Top half
            left_arm_faces.append(f_idx)
        if ns[0] > 0.8 and ctr[1] > 0: # Right, Top half
            right_arm_faces.append(f_idx)

    for f in left_arm_faces:
        nid = builder.extrude_face(f, 0.3) # Arm
        nid = builder.extrude_face(nid, 0.3) # Forearm

    for f in right_arm_faces:
        nid = builder.extrude_face(f, 0.3)
        nid = builder.extrude_face(nid, 0.3)
        
    # 5. HARDENING: Apply Creases (Shoe Soles & Hands)
    # We detect edges based on position.
    # Feet Soles: Edges where both vertices have Y < 0.1 (Base is 0 at start, but we moved center?)
    # We haven't moved center yet. Verticies are around 0.
    # We extruded LEGS down. 
    # Let's check bounding box.
    min_y = 999.0
    max_x = -999.0
    for v in torso.vertices:
        if v[1] < min_y: min_y = v[1]
        if abs(v[0]) > max_x: max_x = abs(v[0])
        
    # Detect Soles (Y close to min_y)
    sole_threshold = min_y + 0.05
    hand_threshold = max_x - 0.05
    
    creases = []
    
    # Iterate all edges in mesh
    # We need to build edge set from faces
    edges_set = set()
    for face in torso.faces:
        n = len(face)
        for i in range(n):
            u, v = face[i], face[(i+1)%n]
            edges_set.add(tuple(sorted((u, v))))
            
    for e in edges_set:
        v1 = torso.vertices[e[0]]
        v2 = torso.vertices[e[1]]
        
        # Check Sole Rule
        if v1[1] < sole_threshold and v2[1] < sole_threshold:
            creases.append([e[0], e[1]])
            
        # Check Hand Rule (Sharp fists)
        # if abs(v1[0]) > hand_threshold and abs(v2[0]) > hand_threshold:
        #     creases.append([e[0], e[1]])
            
    torso.crease_edges = creases
        
    # 6. FINAL SMOOTHING
    # Run CC again to smooth the extrusions.
    mesh_engine.execute_instruction(AgentMeshInstruction(op_code="SUBDIVIDE", params={"iterations": 2}, target_id=torso.id))
    
    # 7. Apply Material Tag
    # It's one mesh now. Gradient material?
    
    # 7. Skeleton
    # We need to autorig this blob.
    # Our AutoRig assumes generic proportions.
    # We used roughly human props.
    # Root is at 0,0,0 (center of torso original).
    # Legs went DOWN (-0.8). Head went UP (+X).
    # We need to OFFSET the mesh to sit on ground (Torso is at ~0.9m).
    for idx, v in enumerate(torso.vertices):
         # v is list [x,y,z]
         torso.vertices[idx] = [v[0], v[1] + 0.9, v[2]]
        
    skel = anim_engine.execute_instruction(type("IA", (), {"op_code": "AUTO_RIG", "params": {}, "target_skeleton_id": None})())
    
    # 8. Auto-Skinning (Rigid Binding or Heatmap)
    # We assign weights based on proximity to bone line segments.
    # We need bone Map to lookup positions (AutoRig creates them with absolute positions).
    
    # Build fast bone lookup
    # Bone Segment: Line from HeadPos to TailPos
    bones = [(b.id, b.head_pos, b.tail_pos) for b in skel.bones]
    
    skin_weights = []
    
    for v in torso.vertices:
        # Find closest bone
        best_dist = 99999.0
        best_bone = ""
        
        for bid, h, t in bones:
            d = _point_line_segment_distance(v, h, t)
            if d < best_dist:
                best_dist = d
                best_bone = bid
                
        # Assign 1.0 to best bone (Rigid Skinning for Fortnite look is okay, or simple blend?)
        # Let's do simple blend of top 2 if close?
        # For robustness in V1: Rigid Binding (100% to nearest).
        # This keeps limbs solid.
        skin_weights.append({best_bone: 1.0})
        
    torso.skin_weights = skin_weights
    
    # 9. TEXTURING: Calculate Box UVs
    # Mapping u,v based on position and normal.
    # Simple Box Map:
    # If Normal.x dominant -> uv = y,z
    # If Normal.y dominant -> uv = x,z
    # If Normal.z dominant -> uv = x,y
    
    uvs = []
    # Recompute normals for UVs (since geometry changed)
    # We need per-vertex normals. Smooth shading normals.
    # Approximate normal = normalized position relative to local center? No.
    # Let's use simple planar projection based on vertex position.
    
    for v in torso.vertices:
        # Check dominant axis via position or mock normal?
        # Mock normal: We know legs are vertical, arms horizontal.
        # Let's just project XZ (Top) for Head/Shoulders, XY (Front) for Body?
        # Standard Box Map:
        # Use position to determine face?
        # Or Just Cylindrical Map for Body?
        # Cylindrical is better for Character.
        # U = angle around Y. V = height Y.
        
        # Center: ~0,0,0 (after we moved them? No, we moved +0.9)
        # Rel pos:
        rx = v[0]
        ry = v[1] - 0.9 # relative to pelvis
        rz = v[2]
        
        # Angle
        theta = math.atan2(rx, rz) # -pi to pi
        u = (theta / (2*math.pi)) + 0.5
        v_coord = ry * 0.5 + 0.5 # Scale Y to 0-1 range approx (Height 1.8m)
        
        uvs.append([u, v_coord])
        
    torso.uvs = uvs

    return skel.id, torso.id

def _point_line_segment_distance(pt, v, w):
    # dist squared or real? Real.
    # l2 = dist_sq(v, w)
    l2 = (v[0]-w[0])**2 + (v[1]-w[1])**2 + (v[2]-w[2])**2
    if l2 == 0: return ((pt[0]-v[0])**2 + (pt[1]-v[1])**2 + (pt[2]-v[2])**2)**0.5
    
    # t = dot(p-v, w-v) / l2
    t = ((pt[0]-v[0])*(w[0]-v[0]) + (pt[1]-v[1])*(w[1]-v[1]) + (pt[2]-v[2])*(w[2]-v[2])) / l2
    
    # clamp 0, 1
    t = max(0, min(1, t))
    
    # proj = v + t * (w - v)
    px = v[0] + t * (w[0]-v[0])
    py = v[1] + t * (w[1]-v[1])
    pz = v[2] + t * (w[2]-v[2])
    
    return ((pt[0]-px)**2 + (pt[1]-py)**2 + (pt[2]-pz)**2)**0.5

def _compute_normal(mesh, face_indices):
    p0 = mesh.vertices[face_indices[0]]
    p1 = mesh.vertices[face_indices[1]]
    p2 = mesh.vertices[face_indices[2]]
    u = [p1[0]-p0[0], p1[1]-p0[1], p1[2]-p0[2]]
    v = [p2[0]-p0[0], p2[1]-p0[1], p2[2]-p0[2]]
    nx = u[1]*v[2] - u[2]*v[1]
    ny = u[2]*v[0] - u[0]*v[2]
    nz = u[0]*v[1] - u[1]*v[0]
    l = (nx**2+ny**2+nz**2)**0.5
    if l==0: return [0,1,0]
    return [nx/l, ny/l, nz/l]
