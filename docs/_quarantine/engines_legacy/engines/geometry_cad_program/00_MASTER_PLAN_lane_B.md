Geometry & CAD Muscle Program – Lane B (Avatar + CAD)

This lane finishes avatar/scene muscle for a serious builder and implements CAD ingest → semantics → BoQ → cost → plan-of-works → diff/risk/portfolio per the CAD P0–P15 roadmap. Run phases in order.

Avatar Muscle (final pass)
- PHASE_AV01: Rig & Morph Foundations (rig correctness, morph targets, retargeting hooks)
- PHASE_AV02: Parametric Avatar Builder (sliders/controls, presets, kits, history)
- PHASE_AV03: Asset Kits & Materials (outfits/props/hair, materials/UV checks, library)
- PHASE_AV04: Animation & Export (motion library, FK/IK mixer, USD/GLTF export)
  - Detailed execution for each phase lives in the PHASE_AV0x docs; run them in order.

CAD Muscle (P0–P15 aligned)
- PHASE_CAD01: CAD Ingest P0–P2 (file intake, normalization, topology healing)
- PHASE_CAD02: Semantics P3–P5 (element classification, layers, spatial graph)
- PHASE_CAD03: Quantities P6 (BoQ extraction, units, scopes)
- PHASE_CAD04: Costing P7–P8 (cost library, rate application, currency/versioning)
- PHASE_CAD05: Plan-of-Works P9 (tasks, sequencing, durations, resources)
- PHASE_CAD06: Diffs & Change Tracking P10 (version diff, impact mapping)
- PHASE_CAD07: Scenarios/Risk/Compliance P11–P12 (risk scoring, rules, compliance flags)
- PHASE_CAD08: Portfolio & Lifecycle P13–P14 (multi-project rollups, lifecycle states)
- PHASE_CAD09: Integrations & APIs P15 (consolidated APIs, artifacts, determinism)
  - Detailed execution for each phase lives in the PHASE_CAD0x docs; run them in order.

Execution note: Future coding agents should complete each phase (code + tests + docs) then immediately continue to the next phase unless a phase marks TODO – HUMAN DECISION REQUIRED and cannot proceed with defaults.
