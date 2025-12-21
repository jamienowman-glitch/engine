# Phase 8 – Interop & Export: glTF++, STEP/IGES Bridge

**Goal:**  
Improve import and add export; begin bridging toward CAD formats.

**Prompt:**
**glTF:**
- Enhance `gltf_import` to support glTF materials/textures, skinning, animations if feasible without external engines.
- Create `gltf_export.py` to serialize a `SceneV2` into glTF (geometry, materials, hierarchy).

**CAD Bridge:**
- Stub out a `cad_bridge` module.
- Outline a plan for integrating a STEP/IGES parser (no full implementation yet).

**Tests:**
Include tests that round-trip a simple scene through import -> export and verify mesh counts/material data persist.

**Constraint:**
Avoid adding new dependencies unless absolutely necessary; if you need an external CAD parser, document it but don’t integrate.
