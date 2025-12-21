
import json
import struct
import os

def create_minimal_glb(output_path: str):
    """Creates a minimal valid GLB file with a single triangle."""
    
    # 1. Geometry Data (Single Triangle)
    # Positions (vec3 float): (0,0,0), (1,0,0), (0,1,0)
    positions = struct.pack('<fffffffff', 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    # Indices (ushort): 0, 1, 2
    indices = struct.pack('<HHH', 0, 1, 2)
    
    # Padding to 4 bytes
    positions_len = len(positions)
    positions_pad = (4 - (positions_len % 4)) % 4
    positions += b'\x00' * positions_pad
    
    indices_len = len(indices)
    indices_pad = (4 - (indices_len % 4)) % 4
    indices += b'\x00' * indices_pad
    
    buffer_data = positions + indices
    buffer_len = len(buffer_data)
    
    # 2. JSON Chunk
    gltf = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": buffer_len}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(positions), "target": 34962}, # ARRAY_BUFFER
            {"buffer": 0, "byteOffset": len(positions), "byteLength": len(indices), "target": 34963} # ELEMENT_ARRAY_BUFFER
        ],
        "accessors": [
            {
                "bufferView": 0, 
                "byteOffset": 0, 
                "componentType": 5126, # FLOAT
                "count": 3, 
                "type": "VEC3",
                "max": [1.0, 1.0, 0.0],
                "min": [0.0, 0.0, 0.0]
            },
            {
                "bufferView": 1, 
                "byteOffset": 0, 
                "componentType": 5123, # UNSIGNED_SHORT
                "count": 3, 
                "type": "SCALAR",
                "max": [2],
                "min": [0]
            }
        ],
        "meshes": [
            {
                "primitives": [
                    {
                        "attributes": {"POSITION": 0},
                        "indices": 1
                    }
                ]
            }
        ],
        "nodes": [
            {"mesh": 0, "name": "HeroAvatarRoot"}
        ],
        "scenes": [
            {"nodes": [0]}
        ],
        "scene": 0
    }
    
    json_bytes = json.dumps(gltf).encode('utf-8')
    json_len = len(json_bytes)
    json_pad = (4 - (json_len % 4)) % 4
    json_bytes += b' ' * json_pad
    json_len = len(json_bytes)
    
    # 3. Headers
    # Magic (4), Version (4), Length (4)
    # Chunk 0: JSON Length (4), Type (4), Data
    # Chunk 1: BIN Length (4), Type (4), Data
    
    total_len = 12 + (8 + json_len) + (8 + buffer_len)
    
    header = struct.pack('<III', 0x46546C67, 2, total_len)
    chunk0_header = struct.pack('<II', json_len, 0x4E4F534A) # JSON
    chunk1_header = struct.pack('<II', buffer_len, 0x004E4942) # BIN
    
    with open(output_path, 'wb') as f:
        f.write(header)
        f.write(chunk0_header)
        f.write(json_bytes)
        f.write(chunk1_header)
        f.write(buffer_data)

if __name__ == "__main__":
    os.makedirs("engines/bot_better_know/assets", exist_ok=True)
    create_minimal_glb("engines/bot_better_know/assets/hero_android_v1.glb")
    print("Created hero_android_v1.glb")
