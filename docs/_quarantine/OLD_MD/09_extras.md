# Phase 9 – Rhino-Adjacent Extras (LoD, Instancing, Scripting Hooks)

**Goal:**  
Add quality-of-life and extensibility features that make the engine feel professional.

**Prompt:**
**LoD:**
Implement Level-of-Detail (LoD) support: allow each mesh to have multiple resolutions and choose based on camera distance in `apply_lod(scene)`.

**Instancing:**
Add explicit instancing: a node can reference another node’s mesh/material instead of duplicating it.

**Scripting:**
Introduce a scripting API: a simple Python function registry that can take a `SceneV2`, run custom logic, and return a modified scene—this is for future plugin hooks.

**Tests:**
Write tests verifying LoD selection, instance referencing, and that scripting hooks can modify node positions via a supplied callback.

**Constraint:**
Keep the scripting system minimal and safe (no arbitrary file IO or network).
