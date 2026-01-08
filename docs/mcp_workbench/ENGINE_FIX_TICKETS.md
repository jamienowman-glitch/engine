# ENGINE FIX TICKETS

## Identity & Envelope Critical Fixes

### ENG-STD-001: Chat WS Transport
- **Router**: `engines.chat.service.ws_transport`
- **Files**: `engines/chat/service/ws_transport.py`
- **Scope**:
    - [ ] Injecct `RequestContext` (Header/Query param based for WS?).
    - [ ] Wrap errors in `ErrorEnvelope`.
- **Acceptance**:
    - WS connection rejected without auth context.
    - Errors return JSON envelope before close.

### ENG-STD-002: Chat SSE Transport
- **Router**: `engines.chat.service.sse_transport`
- **Files**: `engines/chat/service/sse_transport.py`
- **Scope**:
    - [ ] Ensure `ErrorEnvelope` on connect errors.
- **Acceptance**:
    - Connect error returns correct JSON structure.

### ENG-STD-003: Video Mask Routes
- **Router**: `engines.video_mask.routes`
- **Files**: `engines/muscle/video_mask/routes.py`
- **Scope**:
    - [ ] Add `ctx: RequestContext = Depends(get_request_context)`.
    - [ ] Convert returns to `Envelope`.
- **Acceptance**:
    - Endpoint returns 422 if headers missing.

### ENG-STD-004: Video Multicam Routes
- **Router**: `engines.video_multicam.routes`
- **Files**: `engines/muscle/video_multicam/routes.py`
- **Scope**:
    - [ ] Add Identity.
    - [ ] Add Envelope.

### ENG-STD-005: Audio Semantic Timeline Routes
- **Router**: `engines.audio_semantic_timeline.routes`
- **Files**: `engines/muscle/audio_semantic_timeline/routes.py`
- **Scope**:
    - [ ] Add Identity.
    - [ ] Add Envelope.

### ENG-STD-006: Video Presets Routes
- **Router**: `engines.video_presets.routes`
- **Files**: `engines/muscle/video_presets/routes.py`
- **Scope**:
    - [ ] Add Identity.
    - [ ] Add Envelope.

### ENG-STD-007: Video Text Routes
- **Router**: `engines.video_text.routes`
- **Files**: `engines/muscle/video_text/routes.py`
- **Scope**:
    - [ ] Add Identity.
    - [ ] Add Envelope.

### ENG-STD-008: Routing Routes
- **Router**: `engines.routing.routes`
- **Files**: `engines/routing/routes.py`
- **Scope**:
    - [ ] Add Identity.
    - [ ] Add Envelope.

### ENG-STD-009: Canvas Stream Router
- **Router**: `engines.canvas_stream.router`
- **Files**: `engines/canvas_stream/router.py`
- **Scope**:
    - [ ] Add Identity.
    - [ ] Add Envelope.

## Envelope-Only Fixes (Identity Passed)

### ENG-STD-010: Chat Routes
- **Router**: `engines.chat.service.routes`
- **Files**: `engines/chat/service/routes.py`
- **Scope**:
    - [ ] Wrap returns in `ErrorEnvelope`.

### ENG-STD-011: Media Service Routes
- **Router**: `engines.media.service.routes`
- **Files**: `engines/muscle/media/service/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-012: Maybe Routes
- **Router**: `engines.maybes.routes`
- **Files**: `engines/maybes/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-013: Identity Keys
- **Router**: `engines.identity.routes_keys`
- **Files**: `engines/identity/routes_keys.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-014: Identity Analytics
- **Router**: `engines.identity.routes_analytics`
- **Files**: `engines/identity/routes_analytics.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-015: Identity Control Plane
- **Router**: `engines.identity.routes_control_plane`
- **Files**: `engines/identity/routes_control_plane.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-016: Identity Ticket
- **Router**: `engines.identity.routes_ticket`
- **Files**: `engines/identity/routes_ticket.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-017: Strategy Lock
- **Router**: `engines.strategy_lock.routes`
- **Files**: `engines/strategy_lock/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-018: Temperature
- **Router**: `engines.temperature.routes`
- **Files**: `engines/temperature/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-019: Vector Explorer
- **Router**: `engines.nexus.vector_explorer.routes`
- **Files**: `engines/nexus/vector_explorer/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-020: Vector Ingest
- **Router**: `engines.nexus.vector_explorer.ingest_routes`
- **Files**: `engines/nexus/vector_explorer/ingest_routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-021: Video Timeline
- **Router**: `engines.video_timeline.routes`
- **Files**: `engines/muscle/video_timeline/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-022: Video Render
- **Router**: `engines.video_render.routes`
- **Files**: `engines/muscle/video_render/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-023: Video 360
- **Router**: `engines.video_360.routes`
- **Files**: `engines/muscle/video_360/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-024: Video Regions
- **Router**: `engines.video_regions.routes`
- **Files**: `engines/muscle/video_regions/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-025: Audio Service
- **Router**: `engines.audio_service.routes`
- **Files**: `engines/muscle/audio_service/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-026: Video Visual Meta
- **Router**: `engines.video_visual_meta.routes`
- **Files**: `engines/muscle/video_visual_meta/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-027: Audio Voice Enhance
- **Router**: `engines.audio_voice_enhance.routes`
- **Files**: `engines/muscle/audio_voice_enhance/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-028: Budget
- **Router**: `engines.budget.routes`
- **Files**: `engines/budget/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-029: Billing
- **Router**: `engines.billing.routes`
- **Files**: `engines/billing/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-030: KPI
- **Router**: `engines.kpi.routes`
- **Files**: `engines/kpi/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-031: SEO
- **Router**: `engines.seo.routes`
- **Files**: `engines/seo/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-032: Bossman
- **Router**: `engines.bossman.routes`
- **Files**: `engines/bossman/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-033: AWS Debug
- **Router**: `engines.debug.aws_routes`
- **Files**: `engines/debug/aws_routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-034: Kill Switch
- **Router**: `engines.kill_switch.routes`
- **Files**: `engines/kill_switch/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-035: Knowledge
- **Router**: `engines.knowledge.routes`
- **Files**: `engines/knowledge/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-036: Analytics Events
- **Router**: `engines.analytics_events.routes`
- **Files**: `engines/analytics_events/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-037: Three Wise
- **Router**: `engines.three_wise.routes`
- **Files**: `engines/three_wise/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-038: Firearms
- **Router**: `engines.firearms.routes`
- **Files**: `engines/firearms/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-039: Memory
- **Router**: `engines.memory.routes`
- **Files**: `engines/memory/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-040: Actions
- **Router**: `engines.actions.router`
- **Files**: `engines/actions/router.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-041: Raw Storage
- **Router**: `engines.nexus.raw_storage.routes`
- **Files**: `engines/nexus/raw_storage/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-042: Atoms
- **Router**: `engines.nexus.atoms.routes`
- **Files**: `engines/nexus/atoms/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-043: Cards
- **Router**: `engines.nexus.cards.routes`
- **Files**: `engines/nexus/cards/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-044: Index
- **Router**: `engines.nexus.index.routes`
- **Files**: `engines/nexus/index/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-045: Packs
- **Router**: `engines.nexus.packs.routes`
- **Files**: `engines/nexus/packs/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-046: Settings
- **Router**: `engines.nexus.settings.routes`
- **Files**: `engines/nexus/settings/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-047: Runs
- **Router**: `engines.nexus.runs.routes`
- **Files**: `engines/nexus/runs/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-048: Nexus Memory
- **Router**: `engines.nexus.memory.routes`
- **Files**: `engines/nexus/memory/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-049: Canvas Commands
- **Router**: `engines.canvas_commands`
- **Files**: `engines/canvas_commands/router.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-050: Origin Snippets
- **Router**: `engines.origin_snippets.routes`
- **Files**: `engines/origin_snippets/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-051: Persistence
- **Router**: `engines.persistence.routes`
- **Files**: `engines/persistence/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-052: Feature Flags
- **Router**: `engines.feature_flags.routes`
- **Files**: `engines/feature_flags/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-053: Config Store
- **Router**: `engines.config_store.routes`
- **Files**: `engines/config_store/routes.py`
- **Scope**:
    - [ ] Wrap returns.

### ENG-STD-054: Registry
- **Router**: `engines.registry.routes`
- **Files**: `engines/registry/routes.py`
- **Scope**:
    - [ ] Wrap returns.

## Exceptions

### EX-001: Ops Status
- **Router**: `engines.ops.status`
- **Reason**: Public health check endpoint. No auth required.

### EX-002: Identity Auth
- **Router**: `engines.identity.routes_auth`
- **Reason**: Login/Auth endpoints. Cannot require auth to authenticate.
