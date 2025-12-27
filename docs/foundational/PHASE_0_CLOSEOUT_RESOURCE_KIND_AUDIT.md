# Phase 0 Closeout — Resource Kind Audit (Mounted Routers)

Mounted routers from `engines/chat/service/server.py:68-118` and their resource kinds with current fallback evidence.

| Router (prefix) | Resource kinds / deps | Current fallback risk (evidence) |
| --- | --- | --- |
| /ws, /sse (chat) | chat bus, realtime registry | Chat bus env default redis/localhost with disallowed memory but still env-driven (engines/chat/service/transport_layer.py:65-82); realtime registry default InMemory (engines/realtime/isolation.py:99-106). |
| /media (legacy) | legacy media repo | Check legacy path if used; not primary focus. |
| /media-v2 | media repo, storage bucket | LocalMediaStorage local/tmp fallback (engines/media_v2/service.py:84-102); RAW_BUCKET env required, not registry (engines/media_v2/service.py:55-80). |
| /maybes | maybes repository | Env default InMemory (engines/maybes/repository.py:88-97). |
| /auth, /keys | identity repo, keys | Identity backend hard-fails non-firestore; keys not in scope for closeout. |
| /analytics/events | analytics events repo | Env default InMemory (engines/analytics_events/service.py:22-29). |
| /strategy-lock | strategy lock repo | Env default InMemory (engines/strategy_lock/state.py:8-16). |
| /temperature | temperature repo | Check routing if added later (not a fallback hotspot). |
| /vector-explorer, /vector-ingest | vector store selection | Uses selecta/keys; secrets deferred; routing registry needed later. |
| /video (timeline) | timeline repo | Firestore fallback to InMemory when Firestore fails (engines/video_timeline/service.py:436-445). |
| /video (render, 360, regions, mask, multicam, visual_meta, text, presets) | render/timeline/media deps | InMemory timeline fallback (engines/video_timeline/service.py:436-445); media_v2 storage local/tmp risk (engines/media_v2/service.py:84-102). |
| /audio-service, /audio-semantic, /audio-voice-enhance | media_v2 + models | Inherits media_v2 storage risks. |
| /budget | budget repo | Env default InMemory (engines/budget/repository.py:175-182). |
| /billing | billing repo | Secrets deferred; backend not covered here. |
| /kpi | kpi repo | Env default InMemory (engines/kpi/service.py:13-20). |
| /seo | seo repo | Env default InMemory (engines/seo/service.py:11-18). |
| /bossman | (check separately) | Not primary fallback hotspot. |
| /debug (aws) | aws probes | Uses RequestContext; no backend fallback issue. |
| /kill-switch | kill_switch repo | Firestore fallback to InMemory (engines/kill_switch/service.py:17-19). |
| /analytics-events (duplicate tag) | analytics repo | Same as analytics_events above. |
| /three-wise | three_wise repo | Env default InMemory (engines/three_wise/service.py:22-24). |
| /firearms | firearms repo | Env default InMemory (engines/firearms/repository.py:117-124). |
| /memory | memory repo | Env default InMemory (engines/memory/repository.py:104-111). |
| /raw-storage | S3 presign + metadata | RAW_BUCKET env and deferred check (engines/nexus/raw_storage/repository.py:38-72); no registry routing. |
| /atoms, /cards, /index, /pack, /settings, /runs, /nexus-memory | Nexus backend | NEXUS_BACKEND allows noop (engines/nexus/backends/__init__.py:8-24). |
| /origin-snippets | timeline/media deps | Inherits timeline + media_v2 fallback risks. |
| /canvas-stream | realtime registry | Default InMemory (engines/realtime/isolation.py:99-106). |
| /feature-flags | feature_flags repo | Env default memory (engines/feature_flags/repository.py:54-83). |
