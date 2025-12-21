1. Goal  
Add asset kits (outfits/props/hair), attachment slots, and material/UV validation for production avatars.

North star + Definition of Done  
- North star slice: ReadyPlayerMe-lite kits—apply outfits/props/hair kits to validated rigs with attachment rules and UV/material checks.  
- Definition of Done:  
  - Kit registry with IDs/slots/compatibility; attachment service snaps kits deterministically with scale/position validation.  
  - UV/texel density checks run on kit meshes; material presets applied/tagged.  
  - Tests cover kit apply/incompatibility, UV checks, material tagging, deterministic transforms.

2. Scope (In / Out)  
- In: kit registry, attachment rules, material presets, UV/scale checks, optional kit CRUD.  
- Out: animation/export (next phase), UI/auth/tenant/safety.

3. Modules to touch  
- engines/scene_engine/avatar/*  
- engines/scene_engine/tests/test_avatar_kitbash.py  
- engines/scene_engine/tests/test_avatar_outfits.py (if slots/materials touched)  
- engines/material_kernel/service.py  
- engines/material_kernel/tests/test_material_basic.py  
- engines/mesh_kernel/service.py (UV checks/helpers)  
- engines/mesh_kernel/tests/test_mesh_basic.py  
- docs/engines/geometry_cad_program/PHASE_AV03_asset_kits_and_materials.md  
- docs/engines/ENGINE_INVENTORY.md (only if kit/material schemas referenced)  
- READ-ONLY context: other files.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Kit registry  
  - Define kit registry schema (kit IDs, slots required, compatible body types, default materials/scale) and loader; include versioning.  
  - Provide kit CRUD/list APIs if routes exist; validate on create/update.  
- Attachment service (scene_engine/avatar)  
  - Implement deterministic attachment: snap kit pieces to avatar slots with validated transforms; clamp scale/position; record meta (slot id, kit id).  
  - Reject incompatible slots/body types with clear errors.  
- UV/material validation (mesh_kernel/material_kernel)  
  - Add UV overlap/texel density checks for kit meshes; surface warnings/errors.  
  - Integrate material_kernel presets: apply to kits/slots, tag applied materials, allow per-face overrides while preserving groups.  
- Metadata/history  
  - Persist kit application metadata on scene nodes (slot id, kit id, materials used) for export.  
- Validation & safety  
  - Clear errors for missing assets/slots; maintain backward compatibility.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

5. Tests  
- engines/scene_engine/tests/test_avatar_kitbash.py and test_avatar_outfits.py: kit apply adds nodes/materials correctly; incompatible slot rejection; deterministic transforms/meta.  
- engines/mesh_kernel/tests/test_mesh_basic.py: UV overlap/texel density checks catch bad meshes.  
- engines/material_kernel/tests/test_material_basic.py: preset application to kit meshes and tagging.  
Additional required cases:  
- Registry load test with invalid entries rejected.  
- Determinism: same kit + slot -> same transform/meta.

6. Docs & examples  
- Update this phase doc with kit registry format, attachment rules, material/UV validation thresholds.  
- Add example: apply “casual outfit” kit to avatar, validate UVs, apply material preset, record meta, export-ready node data.  
- Note any registry/model changes in ENGINE_INVENTORY if needed.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If you need a new artifact kind or model field, mark CONTRACT CHANGE in this doc and only update explicitly listed files/tests.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.  
- Within the allow-list, implement all code/tests/docs to reach the Definition of Done; no TODOs unless a blocking external dependency is documented.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Deliver full Definition of Done with passing tests. Then proceed to PHASE_AV04 unless a TODO – HUMAN DECISION REQUIRED truly blocks you.
