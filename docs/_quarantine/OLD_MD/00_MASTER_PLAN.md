# Northstar 3D Program – MASTER PLAN (v0)

**Owner:** CONTROL TOWER
**Repos:**  
- Backend engines: `northstar-engines`  
- Frontends: `agentflow` (+ future apps)

**Core constraint:**  
All 3D work stays **backend-first** and **engine-centric**. Frontends are just viewers/tools on top.

**Hard safety rule (for every phase):**

> Do NOT touch tenants, users, roles, auth, RequestContext, keys, BYOK, Firestore layouts, budgets, or Haze/GET /scene.  
> If something smells multi-tenant, stop and add:
> `# NOTE: tenant/user scoping deferred – will integrate with core spine later.`

---

## Phase Index

- [x] **Phase 0 – Foundations Recap** (Foundation Established)
- [x] **Phase 1 – Constraints v1** (Implemented SceneConstraint, Solver, Presets)
- [x] **Phase 2 – Param / Graph v1** (SceneV2 + BBK sliders) [See Plan](./02_params_v1.md)
- [x] **Phase 3 – Mesh Ops & Geometry Tools v1** [See Plan](./03_mesh_ops.md)
- [x] **Phase 4 – Curves, Surfaces & NURBS Core v1** [See Plan](./04_curves_nurbs.md)
- [x] **Phase 5 – Sketch & Dimensional Constraint System v1** [See Plan](./05_sketch_constraints.md)
- [x] **Phase 6 – Param Graph v2** (Grasshopper baby) [See Plan](./06_grasshopper_lite.md)
- [x] **Phase 7 – Editor Spine** (Tools, Undo/Redo, Selection, Snapping) [See Plan](./07_editor_spine.md)
- [x] **Phase 8 – Interop & Export** (glTF++, STEP/IGES) [See Plan](./08_interop_export.md)
- [x] **Phase 9 – Rhino-adjacent Extras** (LoD, instancing, scripting hooks) [See Plan](./09_extras.md)

---

## Agent Mode: How to Use This Plan

When running an agent against this document:

1. **Pick a Phase** that is not yet marked DONE.
2. Read the **Phase Goal**, **In Scope**, **Out of Scope**, and **Repo Targets**.
3. Open the linked **Phase Plan File** (e.g. `02_params_v1.md`).
4. Execute the prompt contained within that file.
5. After verification, mark the Phase as **DONE** here.
