# Phase 7 – Editor Spine: Tools, Undo/Redo, Selection, Snapping

**Goal:**  
Harden the editing infrastructure so interactive tools can operate with confidence and history is reliable.

**Prompt:**
Build a proper `HistoryEngine` if not already finished:
- Model `EditCommands` with before/after diffs.
- Stacks for undo/redo.
- `apply` / `undo` / `redo` methods.

**Tools:**
- Create a `Tool` abstraction (move, rotate, scale) that uses constraints when possible (e.g. move constrained to plane or axis).
- Provide selection utilities: raycast to select nodes, box-select API.
- Add snapping functions: snap to grid, vertices, midpoints.

**Tests:**
Write tests under `tests/test_edit_tools.py` and `tests/test_history_engine.py` that cover:
- Applying multiple commands.
- Undo/redo cycles.
- Snapping and selection logic.

**Constraint:**
Keep everything in-memory; no UI.
