# Phase P15 – Mix Snapshot and Delta Analyzer

Goal: Capture mix states (track/bus gains, FX parameters, master metrics) and compute deterministic diffs between snapshots with simple complexity metrics.

Scope
- In: mix snapshot capture, delta computation, complexity metrics, storage as artifacts/meta, docs/tests.
- Out: video, UI, auth/spine/connectors, unrelated engines.

Modules / files to touch
- engines/audio_mix_snapshot/service.py, models.py (new)
- engines/audio_mix_snapshot/delta.py for comparison logic
- engines/audio_mix_buses/audio_render integration to emit snapshots on demand
- media_v2 artifacts for snapshots (`audio_mix_snapshot`) with meta
- Tests under engines/audio_mix_snapshot/tests
- Docs: docs/engines/audio_program/PHASE_P15_mix_snapshot_delta.md

Implementation steps
1) Snapshot model: capture per-track/bus gain, pan, FX params (reference preset ids + overrides), master loudness/crest factor, plugin count/estimated cpu cost; store with timestamp and backend_version.
2) Capture API: SnapshotRequest {project_id or render_plan, include_buses?, include_fx_params?, include_complexity=true}; SnapshotResult {snapshot_id, uri, meta}.
3) Delta: compare two snapshots; output changes (numeric deltas, added/removed tracks/buses, preset changes); compute complexity change (plugin count/cpu estimate differences).
4) Storage: register snapshots as JSON artifacts in media_v2; ensure deterministic ordering of fields for hashing.
5) Integration: optional hook in audio_render to emit snapshot before/after render when requested; ensure no runtime penalty by keeping capture lightweight.

Tests
- Happy: capture snapshot from seeded mix graph; delta reports expected gain/FX changes; complexity metrics computed.
- Edge: missing tracks between snapshots, empty FX params, floating point tolerances; ensure deterministic field ordering.
- Regression: snapshot hash stable across runs with same inputs.

Safety / non-goals
- No tenant/auth changes; no UI.
- Do not introduce orchestration; keep data-only analysis.

On completion of Phase P15:
- Program complete. Return to master audio plan index for any follow-up or new phases.
