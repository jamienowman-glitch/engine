# Phase 0.6 — Analytics/UTM/SEO/Typo Parallel Plan

## Two-worker split
- Worker A (Engines telemetry): normalization application, analytics_events durability, SEO durability/AEO hook, agent-readable list routes, GateChain behavior unchanged.
- Worker B (UI + typography/muscle): UTM builder + transport headers, UI analytics calls, variable font/typography data/presets/per-letter controls; add fonts via data-only path.

## Three-worker split
- Worker A: analytics_events repo/service/routes (filesystem default), alias normalization, list/read endpoints for agents.
- Worker B: SEO repo/service/routes durability + AEO measurement hook.
- Worker C: UI/muscle typography + UTM propagation (variable fonts, per-letter controls, font registry data adds).

Ordering/merge rules
1) Normalization + durability (A/B) can proceed in parallel; no shared files with UI.
2) Typography/UTM changes can land independently; ensure acceptance uses updated endpoints.
3) Coordinate any shared context/headers to avoid drift (use RequestContext keys).
