# Scene Engine v1 Plan

This is the single source of truth for the Scene Engine v1 plan.

- **Architect:** Gem
- **Implementer:** Max
- **QA:** Claude

## A. Backlog / Context

The **Scene Engine** is a headless service that composes 2-D or 3-D layout data into a standard 3-D Scene JSON. This allows any viewer (Multi²¹, BBK Studio, Shops, etc.) to render a consistent scene from neutral input.

**Core principles:**
- **Headless:** The engine does NOT render anything. It is not a UI component. Its only output is data (JSON).
- **Neutral:** It is agnostic to the *meaning* of the content. It takes a grid, a list of boxes, and a layout "recipe," and maps them into a 3-D scene. It doesn't know or care if the boxes represent videos, products, or data points.
- **Composable:** The engine itself is composed of smaller, single-purpose engines (grid normalization, world mapping, recipes) that will be registered in the main engine registry.
- **Cloud-Portable:** It will be packaged as a standard container (Docker) for deployment anywhere.

> **Implementation note (SE-01 v1):** Implement the Scene Engine service in **Python 3.12** using **FastAPI** for HTTP, **Pydantic** for schemas/validation, and **pytest** for tests.

---

### Input Contract

The engine accepts a JSON object with the following shape:

```json
{
  "grid": {
    "cols": 24,
    "rows": 1, 
    "col_width": 1.0,
    "row_height": 1.0
  },
  "boxes": [
    {
      "id": "unique-box-id-1",
      "x": 0,
      "y": 0,
      "z": 0,
      "w": 4,
      "h": 3,
      "d": 1,
      "kind": "card",
      "meta": {
        "title": "Example Card"
      }
    }
  ],
  "recipe": "wall"
}
```
- **`grid`**: Defines the logical grid space.
  - `cols`: Number of columns (default should be configurable, not hard-locked).
  - `rows`: Optional number of rows.
- **`boxes[]`**: A list of objects to place on the grid. Coordinates are in **grid units**, not pixels.
  - `id`: A unique identifier for the box.
  - `x`, `y`, `z`: The starting coordinates of the box on the grid. `z` is optional, defaults to `0`.
  - `w`, `h`, `d`: The dimensions of the box in grid units. `d` (depth) is optional, defaults to `1`.
  - `kind`: A string indicating the type of node, e.g., `"card"`, `"point"`, `"mesh"`.
  - `meta`: A freeform object for the caller to attach any data. The Scene Engine passes this through untouched.
- **`recipe`** (string): The name of the layout algorithm to apply, e.g., `"wall"`, `"vector_explorer"`.

---

### Output Contract (Scene JSON)

The engine returns a standard Scene JSON object:

```json
{
  "sceneId": "generated-scene-uuid",
  "nodes": [
    {
      "id": "unique-box-id-1",
      "kind": "card",
      "gridBox3D": {
        "x": 0, "y": 0, "z": 0,
        "w": 4, "h": 3, "d": 1
      },
      "worldPosition": {
        "x": -10.0, "y": 1.5, "z": 0.0
      },
      "meta": {
        "title": "Example Card"
      }
    }
  ],
  "camera": {
    "position": [0, 5, 20],
    "target": [0, 5, 0],
    "mode": "perspective"
  }
}
```
- **`sceneId`**: A unique ID for the generated scene.
- **`nodes[]`**: A list of scene objects.
  - `id`: The original box ID.
  - `kind`: The original `kind`.
  - `gridBox3D`: The fully-specified grid position and dimensions.
  - `worldPosition`: The calculated `x, y, z` coordinates in 3-D world space.
  - `meta`: The original `meta` object, passed through.
- **`camera`**: A minimal description of a suggested camera setup for viewing the scene.

---

## B. Active Task (only ONE active)

### Task ID: SE-01 – CORE_SCENE_ENGINE_V1

1.  **Goal**
    Implement a **Scene Engine v1** as an HTTP service that:
    - Accepts `POST /scene/build` with `{ grid, boxes, recipe }`.
    - Returns Scene JSON matching the contract defined in section A.
    - Supports at least two recipes: `"wall"` (flat wall of cards) and `"vector_explorer"` (simple 3-D scatter plot).
    - Is architected with composable internal engines (grid normaliser, layout mapper, vector projector).
    - Is packaged as a Docker container for local execution.
    - Includes minimal logging and a `/health` endpoint.

2.  **Files to touch (for Max)**
    - `engines/scene-engine/` (root for this engine)
      - `engines/scene-engine/service/` (HTTP service, handlers, schemas)
      - `engines/scene-engine/core/` (Pure engine logic: grid normalisation, mapping, recipes)
        - `engines/scene-engine/core/recipes/`
      - `engines/scene-engine/tests/` (Unit and integration tests)
      - `engines/scene-engine/Dockerfile`
      - `engines/scene-engine/scripts/run_local.sh` (Optional helper)
    - Registry touchpoints:
      - `docs/engines/ENGINE_REGISTRY.md`
      - `engines/registry/engine_registry.json`
      - `engines/registry/engine_combos.json`
    - Logs:
      - `docs/logs/ENGINES_LOG.md` (Create if it doesn't exist)

3.  **Assumptions & defaults for Max (SE-01):**
    - If the plan leaves a detail open (e.g. minor naming), you MUST:
      - Choose a reasonable default consistent with this repo's tech stack: Python 3.12, FastAPI, Pydantic, pytest, `PORT=8080`.
      - Note the assumption in `docs/logs/ENGINES_LOG.md` for the relevant phase (e.g., `ASSUMPTION: Used X as the name for Y.`).
      - Do **not** stop to ask the user; keep moving and log what you decided.

4.  **Phases (SE-01.x)**

---

#### Phase SE-01.A – Contracts & Types

- **Goal:** Lock the input/output contracts and basic type definitions so all other modules can build on them.
- **Files (Max):**
  - `engines/scene-engine/service/schemas.py`
  - `engines/scene-engine/core/types.py`
  - `docs/20_SCENE_ENGINE_PLAN.md` (status update only)
- **Steps (Max / Implementer):**
  1.  Create core type/schema definitions using Pydantic for: `Grid`, `Box`, `Recipe` (Enum), `Scene`, `SceneNode`, `Camera`.
  2.  Ensure types are neutral (no UI-specific logic, no pixel units).
  3.  Add minimal tests to validate basic type usage or schema validation rules.
- **Logging & Status (Max):**
  - Append to `docs/logs/ENGINES_LOG.md`: `YYYY-MM-DD · SE-01.A · Done · Defined Scene Engine contracts + types.`
  - In `docs/20_SCENE_ENGINE_PLAN.md`, update the phase header to: `#### ✅ Phase SE-01.A – Contracts & Types`

---

#### Phase SE-01.B – HTTP Service Skeleton

- **Goal:** Have a running, but "dumb," HTTP service with the correct endpoints and basic validation.
- **Files (Max):**
  - `engines/scene-engine/service/server.py`
  - `engines/scene-engine/service/routes.py`
  - `engines/scene-engine/tests/test_service_basic.py`
- **Steps (Max / Implementer):**
  1.  Implement a basic FastAPI web service.
  2.  Create endpoint `GET /health` which returns `{"status": "ok"}`.
  3.  Create endpoint `POST /scene/build` that accepts a request body validated by the schemas from SE-01.A. For now, it can return a hardcoded, minimal Scene JSON.
  4.  Add tests for the `/health` endpoint and a basic `POST /scene/build` roundtrip to confirm validation works.
- **Logging & Status (Max):**
  - Append to `docs/logs/ENGINES_LOG.md`: `YYYY-MM-DD · SE-01.B · Done · Implemented HTTP service skeleton with /health and /scene/build endpoints.`
  - In `docs/20_SCENE_ENGINE_PLAN.md`, update the phase header to: `#### ✅ Phase SE-01.B – HTTP Service Skeleton`

---

#### Phase SE-01.C – Grid & Box Normalisation Engine

- **Goal:** Create a small, pure internal engine that normalises grid and box data into a fully-specified 3-D grid space.
- **Files (Max):**
  - `engines/scene-engine/core/grid_normaliser.py`
  - `engines/scene-engine/tests/test_grid_normaliser.py`
- **Steps (Max / Implementer):**
  1.  Implement a pure function (no IO, no service logic) that takes `{ grid, boxes }`.
  2.  It must fill in defaults for optional fields (e.g., `z = 0`, `d = 1` for boxes).
  3.  It should validate that all coordinates are valid numbers (int/float) in grid units.
  4.  Add unit tests to verify that missing fields are defaulted correctly and that bad inputs raise appropriate, specific errors.
- **Logging & Status (Max):**
  - Append to `docs/logs/ENGINES_LOG.md`: `YYYY-MM-DD · SE-01.C · Done · Created grid and box normalisation engine.`
  - In `docs/20_SCENE_ENGINE_PLAN.md`, update the phase header to: `#### ✅ Phase SE-01.C – Grid & Box Normalisation Engine`

---

#### Phase SE-01.D – Grid→World Mapping & Recipes ("wall" + "vector_explorer")

- **Goal:** Turn normalised grid boxes into world positions and implement the first two recipes.
- **Files (Max):**
  - `engines/scene-engine/core/mapping.py`
  - `engines/scene-engine/core/recipes/wall.py`
  - `engines/scene-engine/core/recipes/vector_explorer.py`
  - `engines/scene-engine/tests/test_mapping.py`
  - `engines/scene-engine/tests/test_recipes.py`
- **Steps (Max / Implementer):**
  1.  Implement a `GridToWorldMapper` that converts a `gridBox3D` into a `worldPosition`. Choose sensible basis vectors (e.g., `X` right, `Y` up, `Z` forward) and an origin.
  2.  Implement the `"wall"` recipe: a pure function that takes normalised boxes and lays them out on a flat plane at `z = 0`.
  3.  Implement the `"vector_explorer"` recipe: a pure function that uses vector data from `box.meta` to influence `z` position or other attributes.
  4.  Wire the normaliser (SE-01.C) and these new modules into the `POST /scene/build` endpoint. The endpoint should now execute the full pipeline.
  5.  Add tests to verify that a "wall" scene produces the expected node layout and that the "vector_explorer" produces nodes with varying world positions.
- **Logging & Status (Max):**
  - Append to `docs/logs/ENGINES_LOG.md`: `YYYY-MM-DD · SE-01.D · Done · Implemented grid-to-world mapping and two recipes (wall, vector_explorer).`
  - In `docs/20_SCENE_ENGINE_PLAN.md`, update the phase header to: `#### ✅ Phase SE-01.D – Grid→World Mapping & Recipes`

---

#### Phase SE-01.E – Engines Registry Hooks

- **Goal:** Register the Scene Engine’s internal components in the global engines registry.
- **Files (Max):**
  - `docs/engines/ENGINE_REGISTRY.md`
  - `engines/registry/engine_registry.json`
  - `engines/registry/engine_combos.json`
- **Steps (Max / Implementer):**
  1.  In `engine_registry.json`, define atomic engine entries: `SCENE.GRID.NORMALISE_V1`, `SCENE.GRID.MAP_TO_WORLD_V1`, `SCENE.RECIPE.WALL_V1`, `SCENE.RECIPE.VECTOR_EXPLORER_V1`.
  2.  For each, specify: ID, label, category (`"SCENE"`), primary module path, a description of inputs/outputs, and notes.
  3.  In `engine_combos.json`, define combo entries: `SCENE.BUILD_WALL_V1` (chains normaliser + mapper + wall) and `SCENE.BUILD_VECTOR_EXPLORER_V1` (chains normaliser + mapper + vector explorer).
  4.  Update the markdown `ENGINE_REGISTRY.md` to be a human-readable reflection of the JSON files.
- **Logging & Status (Max):**
  - Append to `docs/logs/ENGINES_LOG.md`: `YYYY-MM-DD · SE-01.E · Done · Registered Scene Engine components in the engine registry.`
  - In `docs/20_SCENE_ENGINE_PLAN.md`, update the phase header to: `#### ✅ Phase SE-01.E – Engines Registry Hooks`

---

#### Phase SE-01.F – Docker & Local Container

- **Goal:** Make the Scene Engine runnable as a standard Docker container locally.
- **Files (Max):**
  - `engines/scene-engine/Dockerfile`
  - `engines/scene-engine/scripts/run_local.sh` (optional)
- **Steps (Max / Implementer):**
  1.  Write a `Dockerfile` that installs dependencies, copies the source code, and runs the service on port 8080. Use a multi-stage build for efficiency.
  2.  Document the simple commands to build and run the container in a new `README.md` inside `engines/scene-engine/`.
      - `docker build -t scene-engine:dev .`
      - `docker run -p 8080:8080 scene-engine:dev`
  3.  Verify that `GET /health` and `POST /scene/build` work by calling the service running inside the container.
- **Logging & Status (Max):**
  - Append to `docs/logs/ENGINES_LOG.md`: `YYYY-MM-DD · SE-01.F · Done · Containerized Scene Engine with Docker.`
  - In `docs/20_SCENE_ENGINE_PLAN.md`, update the phase header to: `#### ✅ Phase SE-01.F – Docker & Local Container`

---

#### Phase SE-01.G – Minimal Deployment Lane (Cloud-ready stub)

- **Goal:** Prepare a simple deployment configuration for a target like GCP Cloud Run, making the service cloud-ready.
- **Files (Max):**
  - `engines/scene-engine/deploy/cloudrun.yaml`
  - A new `docs/ENGINES_DEPLOY_NOTES.md`.
- **Steps (Max / Implementer):**
  1.  Create a minimal `cloudrun.yaml` that defines the service.
  2.  The config should specify the container image to use, memory/cpu limits, and exposed ports.
  3.  Document any required environment variables (e.g., `PORT`) in the new deployment notes file.
  4.  This is a planning step; actual deployment is not required. The goal is to have the configuration file checked in and ready.
- **Logging & Status (Max):**
  - Append to `docs/logs/ENGINES_LOG.md`: `YYYY-MM-DD · SE-01.G · Done · Created stub deployment config for Cloud Run.`
  - In `docs/20_SCENE_ENGINE_PLAN.md`, update the phase header to: `#### ✅ Phase SE-01.G – Minimal Deployment Lane (Cloud-ready stub)`

---

## C. Task Completion Ritual (Max) for SE-01

After all SE-01 phases (A–G) are marked Done:

1.  **Verify:**
    - All phase headers from SE-01.A to SE-01.G are marked with `✅` in `docs/20_SCENE_ENGINE_PLAN.md`.
    - `docs/logs/ENGINES_LOG.md` contains at least one entry for each phase (A-G).
2.  **Update Plan:**
    - Move the entire `Task ID: SE-01 – CORE_SCENE_ENGINE_V1` section from **B. Active Task** to **E. Completed Tasks**.
3.  **Final Log:**
    - Append a final log line to `docs/logs/ENGINES_LOG.md`: `YYYY-MM-DD · SE-01 · Completed · CORE_SCENE_ENGINE_V1 task finished.`
4.  **Halt:**
    - Do NOT begin `SE-02` or any other task. Await a plan update from Gem or new instructions from the user (Bossman).

## D. Future Tasks

- **`SE-02 SCENE_ENGINE_ANIMATIONS_V1`**
  - Context: Add support for describing smooth transitions for camera and nodes when the scene layout changes. This might involve adding `animation` blocks to the Scene JSON.

- **`SE-03 SCENE_ENGINE_LIVE_UPDATES_V1`**
  - Context: Implement SSE (Server-Sent Events) or WebSocket support on a `/scene/subscribe/{sceneId}` endpoint to push partial updates to clients for dynamic scenes.

- **`SE-04 SCENE_ENGINE_ADVANCED_PROJECTION_V1`**
  - Context: Enhance the `"vector_explorer"` recipe with more advanced dimensionality reduction techniques (e.g., UMAP, t-SNE) for richer data visualizations.

- **`SE-05 SCENE_ENGINE_BBK_STUDIO_RECIPES_V1`**
  - Context: Develop recipes specific to the BBK Studio, such as arranging stems, loops, and effects in a 3-D DAW-like interface.

- **`SE-06 SCENE_ENGINE_SHOP_LAYOUT_RECIPES_V1`**
  - Context: Develop recipes for e-commerce, such as dynamic product walls, KPI dashboards, and interactive funnels.

## E. Completed Tasks

*(This section is intentionally empty. Tasks will be moved here upon completion.)*

> QA: Claude will add PASS/FAIL stamps under completed tasks once they are reviewed.