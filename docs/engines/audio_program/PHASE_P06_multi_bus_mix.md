# Phase P6 – Multi-Bus Mix Engine

Goal: Move from flat mixdown to bus/group-based mixing with per-bus FX and aligned stems plus master processing.

Scope
- In: audio_mix_buses engine (bus mapping, routing), bus FX chains, master loudnorm/limiter, render updates to mix buses and stems.
- Out: video, UI, auth/spine/connectors, unrelated engines.

Modules / files to touch
- engines/audio_mix_buses/service.py, models.py, routing.py
- engines/audio_mix_buses/presets.py for bus configs (drums, bass, vocals, fx, master)
- engines/audio_render (extend to support bus routing and combined render)
- media_v2 artifact registration for bus stems (`audio_bus_stem`) and master render
- Tests under engines/audio_mix_buses/tests and audio_render/tests
- Docs: docs/engines/audio_program/PHASE_P06_multi_bus_mix.md

Implementation steps
1) Define bus model: BusConfig {id, name, track_roles, fx_chain_id/preset, gain_db, pan?}; MixGraph mapping tracks -> buses -> master.
2) Routing: augment render planner to route clips through assigned bus before master; apply bus-level FX chains (reuse audio_fx_chain where possible); ensure phase-consistent summing.
3) Render outputs: master render plus optional per-bus stems in one pass; align start/end; include meta {bus_map, fx_presets, loudnorm_metrics}.
4) Controls: allow custom bus configs via request; default preset covers drums/bass/vocals/fx.
5) Determinism: fixed processing order, no random modulation; document backend version.

Tests
- Happy: multi-track project with tracks assigned to buses; assert bus stems and master align sample-accurate; bus FX applied (gain/eq) as expected.
- Edge: tracks without bus assignment go to default; conflicting bus presets; extreme levels (ensure limiter prevents clipping).
- Regression: compare bus routing graphs hash to prevent accidental changes.

Safety / non-goals
- No tenant/auth changes; no UI; no orchestration outside engine.

On completion of Phase P6:
- Immediately proceed to Phase P7 using its phase doc.
- Do not pause for human review unless tests fail or you hit an explicit TODO/STOP marker.
