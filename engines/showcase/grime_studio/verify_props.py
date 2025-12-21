"""Verification Script for Grime Studio Generators."""
import sys
import os
# Ensure dev path
sys.path.append(os.getcwd())

from engines.mesh_kernel.service import MeshService
from engines.stage_kernel.service import StageService
from engines.animation_kernel.service import AnimationService
from engines.showcase.grime_studio.generators import gen_decks, gen_mics, gen_studio, gen_robots

def verify_all_props():
    print("🔎 Verifying Grime Studio Props...")
    
    mesh_service = MeshService()
    stage_service = StageService()
    anim_service = AnimationService()
    
    # 1. Deck
    print("Checking CDJ...")
    deck_id = gen_decks.generate_deck(mesh_service)
    gen_decks.register_deck_prop(stage_service, deck_id)
    assert deck_id in mesh_service._store
    assert "prop_cdj" in stage_service._prop_library
    print(f"✅ CDJ Verified (Verts: {len(mesh_service._store[deck_id].vertices)})")
    
    # 2. Mic
    print("Checking Mic...")
    mic_id = gen_mics.generate_mic(mesh_service)
    gen_mics.register_mic_prop(stage_service, mic_id)
    assert mic_id in mesh_service._store
    assert "prop_mic_handheld" in stage_service._prop_library
    print(f"✅ Mic Verified (Verts: {len(mesh_service._store[mic_id].vertices)})")
    
    # 3. Studio
    print("Checking Studio Kit...")
    spk_id = gen_studio.generate_speaker(mesh_service)
    tbl_id = gen_studio.generate_table(mesh_service)
    gen_studio.register_studio_props(stage_service, spk_id, tbl_id)
    assert spk_id in mesh_service._store
    assert tbl_id in mesh_service._store
    assert "prop_speaker" in stage_service._prop_library
    assert "prop_table" in stage_service._prop_library
    print(f"✅ Studio Verified")

    # 4. Robots
    print("Checking The Crew...")
    sel_mesh, sel_skel = gen_robots.generate_selecta_bot(mesh_service, anim_service)
    assert sel_mesh in mesh_service._store
    assert sel_skel is not None
    print(f"✅ Selecta_Bot Verified (Mesh: {sel_mesh}, Skel: {sel_skel})")
    
    spit_mesh, spit_skel = gen_robots.generate_spit_bot(mesh_service, anim_service, variant=1)
    assert spit_mesh in mesh_service._store
    assert spit_skel is not None
    print(f"✅ Spit_Bot_1 Verified (Mesh: {spit_mesh}, Skel: {spit_skel})")

    print("\n🎉 ALL GENERATORS PASS.")

if __name__ == "__main__":
    verify_all_props()
