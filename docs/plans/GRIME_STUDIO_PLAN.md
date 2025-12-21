# GRIME STUDIO: Implementation Plan

**Objective:** Create a hyper-realistic, animated 3D recording studio with 3 autonomous robot avatars (1 DJ, 2 MCs) performing live.
**Constraint:** "Full Gas" usage of Northstar Engines. No legacy assets.

---

## 1. The Environment: "The Booth"
We will build the studio not as a single mesh, but as a composed Stage of highly detailed Props modeled by the Mesh Engine.

### 1.1. The Architecture
*   **Acoustic Treatment**: Use `PRIMITIVE:CUBE` + `SCULPT:INFLATE` (patterned) to generate foam tiles.
*   **Glass Partition**: `PRIMITIVE:PLANE` with `MATERIAL:GLASS` (Transparency/Refraction).
*   **Lighting**:
    *   **Mood**: Dark, moody club vibe.
    *   **Setup**: Overhead soft panel (Area Light), Deck uplighting (Spot), MC rim lights (Blue/Red).

### 1.2. The Kit (Props)
We need to model specific high-fidelity assets using `MeshService`:
*   **The Decks (CDJs)**: Complex Boolean assembly.
    *   Base: Box.
    *   Platter: Cylinder (Difference boolean for recess).
    *   Knobs: Instanced small cylinders.
    *   Screen: Emissive Material.
*   **The Mixer**: similar box+knob construction.
*   **The Mics**:
    *   Handle: Cylinder.
    *   Grill: Sphere + `MATERIAL:WIRE_MESH` (Alpha Mask).
*   **The Speakers**: Large Monitors (Box + Cone extrusions).

---

## 2. The Cast: "The Robots"
3 Distinct Agents sharing the `AUTO_RIG` skeleton but with unique Geometry/Materials.

### 2.1. The DJ ("Selecta_Bot")
*   **Mesh**: Boxy, industrial aesthetics. HEAD is a monitor/screen.
*   **Anim**: Shoulders hunched, head bobbing (140BPM), hands on platters.
*   **Rig**: Standard Humanoid + "Headphone" attachment point.

### 2.2. The MCs ("Spit_Bot_01" & "02")
*   **Mesh**: Sleek, performance-optimized. Articulated jaw/face-plate for TTS sync (future).
*   **Anim**: High energy. Hand gestures. **Critical:** Dynamic Mic Holding.
*   **Rig**: Standard Humanoid + "Mic Grip" bone in Hand.

---

## 3. The Tech: Engine Upgrades Required
To achieve the "Mic closer to mouth" fidelity, we need one specific upgrade to the `AnimationService`.

### 3.1. Inverse Kinematics (IK)
*   **Problem**: `PLAY_ANIM` just rotates bones. It's hard to make a hand *perfectly* touch a mouth or a deck platter using just rotation clips.
*   **Solution**: Implement `IK_SOLVE`.
    *   **Token**: `{"op": "IK_SOLVE", "effector": "HAND_R", "target": "HEAD_MOUTH", "chain_length": 3}`.
    *   **Result**: The engine calculates the Elbow and Shoulder angles automatically to ensure the Hand hits the Target.
    *   *Why we need it:* The MC needs to move the mic to their mouth *dynamically* when TTS triggers, then lower it when listening.

---

## 4. Execution Sequence

### Phase 1: Prop Modeling (The Kit)
1.  Detailed script `gen_decks.py` to sculpt the CDJs and Mixer.
2.  Detailed script `gen_studio.py` to build the Room and Mics.

### Phase 2: Character Modeling (The Crew)
1.  Refine `gen_avatar.py` to create distinct "Robot" variants (DJ vs MC).
2.  Apply distinct Materials (Matte Black vs Chrome vs Carbon Fiber).

### Phase 3: The IK Upgrade (The Brains)
1.  Upgrade `AnimationService` to support `TwoBoneIK` (simple trigonometry solver).
2.  Add `IK_TARGET` nodes to the Stage.

### Phase 4: The Show (Integration)
1.  **Director Script**: `grime_showcase.py`.
    *   Spawns Room.
    *   Spawns DJ at Decks.
    *   Spawns MCs at front.
    *   **Loop**:
        *   DJ Hands -> IK to Deck Platter (Scratching motion).
        *   MC Hand -> IK to Mouth (when `is_speaking=True`).
        *   Lights -> Audio Reactive (Flash on kick drum).

---

## 5. File Structure
We will contain this "App" in a dedicated directory to keep it clean.
```
engines/showcase/grime_studio/
├── assets/          # Generated GLBs (cache)
├── generators/      # Prop/Avatar scripts
│   ├── gen_decks.py
│   ├── gen_mics.py
│   └── gen_robots.py
└── director.py      # The runtime orchestrator
```
