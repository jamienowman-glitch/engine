# Avatar Builder Muscle Program (P0 → P15)

## P0 – Solid Avatar Scene Core (you’re ~here already)
**Goal**: Make a single avatar in a scene easy to represent, edit, and save.
**Muscle**:
- [x] `scene_engine` with SceneV2, nodes, meshes, materials, transforms, attachments.
- [ ] Primitive meshes (box/sphere/etc.) for staging.
- [ ] Avatar rig + presets (base male/female/androgynous).
- [ ] Edit + View engines (create/delete/set/pick).

## P1 – Avatar Style & Pose Engine
**Goal**: Turn “static mesh” into something you can style and pose.
**Muscle**:
- [ ] `AvatarStyle` model + engine (body shape, outfit IDs, colors).
- [ ] Pose Engine v1: `PoseDefinition`, `apply_pose`.

## P2 – Constraint Engine v1
**Goal**: Scenes that “make sense physically”.
**Muscle**:
- [ ] `ConstraintKind` (KEEP_ON_PLANE, MAINTAIN_DISTANCE, AIM_AT).
- [ ] `SceneConstraint` model.
- [ ] `solve_constraints` (iterative solver).

## P3 – Param Graph v1
**Goal**: Drive avatar & camera with sliders.
**Muscle**:
- [ ] `ParamNode`, `ParamGraph`.
- [ ] `ParamBinding`.
- [ ] `evaluate_param_graph`.

## P4 – Expression & Micro-Animation Engine
**Goal**: Avatars that feel alive.
**Muscle**:
- [ ] `Expression` model + `apply_expression`.
- [ ] `AnimClip` + `sample_clip_at_time`.

## P5 – Avatar Kitbashing & Export Engine
**Goal**: Reusable kits, export, variations.
**Muscle**:
- [ ] `AvatarKit` engine.
- [ ] Variation engine.
- [ ] Export engine (glTF).

## P6 – Outfit System & Modular Body Parts
**Goal**: Modular kit (swappable outfits, hair).
**Muscle**:
- [ ] `OutfitDefinition`.
- [ ] `BodyPart` variants.

## P7 – Camera Rig & Shot Language Engine
**Goal**: Easy "good shots".
**Muscle**:
- [ ] `CameraRig` model.
- [ ] `ShotDefinition` + `compose_shot`.

## P8 – Environment Kits & Light Presets
**Goal**: One-click environment/lighting.
**Muscle**:
- [ ] `EnvironmentKit` engine.
- [ ] `LightPreset` engine.

## P9 – Avatar Snapshot & Turntable Engine
**Goal**: Consistent exports.
**Muscle**:
- [ ] `avatar_snapshot`.
- [ ] Turntable engine.

## P10 – Avatar Variation & Style Space Explorer
**Goal**: Explore "space of looks".
**Muscle**:
- [ ] Style Space Model.
- [ ] Variation Engine.

## P11 – Multi-Avatar Scenes & Crowd Instancing
**Goal**: Multiple avatars/crowds.
**Muscle**:
- [ ] Spawning helpers.
- [ ] Instancing.

## P12 – Interaction & Contact Engine
**Goal**: Believable interactions.
**Muscle**:
- [ ] `InteractionPose`.
- [ ] Contact solver.

## P13 – Avatar Asset Kit / Marketplace Shape
**Goal**: External parts plugin.
**Muscle**:
- [ ] Asset pack schema.
- [ ] Validation engine.

## P14 – Global Style & Brand Bible Engine
**Goal**: Consistent visual identity.
**Muscle**:
- [ ] Style bible.
- [ ] Enforcement.

## P15 – Avatar Lineage & Evolution Engine
**Goal**: Traceable history.
**Muscle**:
- [ ] Lineage model.
- [ ] Diff engine.
