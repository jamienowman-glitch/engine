Phase 0 — Foundational layer Definition of Done
This is the base substrate that must be true before we do any serious work on logs/safety/memory/realtime/entitlements/artifacts. It’s the “system spine”: identity, tenancy, routing, and real-infra persistence by default.

0.1 Core principle
All runtime decisions are data-driven, not code-driven.
The only acceptable “static wiring” is the minimum needed to boot the system (connect to the control plane). Everything else is routable and changeable without redeploy.

0.2 Canonical primitives and naming

BOSSMAN: THIS NEEDS TO BE HARDENED TO NOT JUST DEFINITIONS BUT ENFORCED AND REAL AND LIVE. 

WE HAVE MISSED USER.  OS>SURFACE>APP>PROJECT

t_system>tenant>user 
Done means we have explicit, non-handwavy definitions for these primitives and their IDs:
Tenant: the primary isolation boundary (tenant_id matches ^t_[a-z0-9_-]+$).


t_system is the control plane tenant.


Everything else is dynamically created (no new hardcoded tenants).


User: belongs to one or more tenants via membership.


Surface: a first-class object that scopes behavior policies + defaults across apps (your “SQUARED² / CUBED³ / …” concept).


App: subscribable product unit that lives on a surface.


Project: optional grouping under tenant/app (if you want it), but defined as a first-class object if it exists.



Acceptance: there is exactly one authoritative place where these concepts are defined + stored + queried (control plane), and all repos can treat it as contract truth.

0.3 Request context contract
Done means the runtime context contract is stable and enforced everywhere:
Every request resolves a RequestContext that includes at least:


tenant_id


a stable partition key (today X-Env exists; we can later rename semantics, but the system needs some partition dimension)


Every protected route has:


auth context (who is the user)


tenant membership check


context match check (payload/route tenant/env must match context)


Error semantics are consistent:


missing auth → 401


wrong tenant / no membership → 403


malformed request → 400


Acceptance: you can hit any mounted router with a valid auth + tenant headers and you don’t get “random 400s” from missing context.

0.4 “Real infra by default” routing spine
This is the big one.
Done means:
There is a Routing Registry (control plane data) that decides “where do we write/read” for each resource kind, scoped at least by:


tenant_id


surface_id (if you want surface-level defaults)


optionally app_id / project_id


Services do not pick backends from scattered env vars at runtime. They ask the routing spine:


“Give me the backend config for feature_flags / memory / kpi / strategy_lock / raw_storage / vector_index / realtime_registry / chat_bus / etc.”


“Defaults” are not hardcoded in service code. Defaults live as data in the control plane (initially set by t_system).


Acceptance: you can switch a tenant from Backend A → Backend B (for at least one category, e.g. feature_flags or memory) without changing code and the system routes correctly.

0.5 Secrets model (without blocking you)
Done means:
Code never hardcodes secret values (already true from your scan).


Code also avoids hardcoding secret names outside a single canonical mapping layer.


There is a single “secret resolution contract” used everywhere (your runtime_config / selecta / keys center is the nucleus):


Local dev today: ADC / local JSON file on laptop is fine.


Cloud Run later: same contract reads from GSM (no app code changes; only the resolver backend changes).


Acceptance: all secret access goes through one resolver interface; no random os.getenv("SOME_SECRET_NAME") scattered across services except the minimum bootstrap necessities.

0.6 Persistence baseline must be real (no in-memory defaults exposed)

BOSSMAN: INMEMORY MUST NOT EXIST FOR UNIT TESTS.  ONLY REAL INFRA. HERE WER SET UP FOR EACH TO HIT THIS BUT DEFINE IN EACH OF (feature flags, strategy lock state, kpi values, budgets, maybes, memory, etc.). IN THEIR INDIVIDUAL DoD
Based on your Oracle scan, multiple routers currently expose in-memory repositories by default (feature_flags, strategy_lock, kpi, budget, maybes, memory, analytics_events, firearms, page_content, seo, rate limiting, realtime registry).
Done means:
For any route mounted in the main app, the default behavior is durable persistence (cloud backend), not InMemory.


InMemory implementations may still exist for unit tests, but must not be reachable by “normal wiring”.


If routing config is missing, the system fails fast with an explicit error pointing to the missing routing entry (not silently using RAM).


Acceptance: restart the service and data still exists for tenant-scoped resources that matter (feature flags, strategy lock state, kpi values, budgets, maybes, memory, etc.).

0.7 Real-time foundation prerequisites (only the substrate, not the “feature”)
BOSSMAN: WE CAN DO REALTIME HERE:  FIRESTORE AS DEFAULT 

You said we’re not doing the full realtime layer DoD yet — but the foundational layer must make it possible.
Done means:
The chat bus backend is a real backend (Redis) and its connection is provided via routing/config contract (not scattered env defaults like localhost).


The realtime registry is durable by default (Firestore, or whichever you choose), not memory.


Acceptance: thread/canvas access control does not evaporate on process restart.

0.8 Tenant “modes” exist as data (no enterprise/saas/lab flags in code)
Oracle says enterprise/saas/lab concepts do not exist in code today.
Done means:
“Enterprise / SaaS / Lab” exists as an entitlement mode object in control plane data, attached to tenant and/or surface.


The rest of the system can query it (but we don’t yet implement all behavior differences — that’s Phase 1/2 work).


Acceptance: you can set a tenant’s mode in the control plane, and the runtime can read and attach it to RequestContext or derived context.

0.9 What Phase 0 explicitly does NOT include
We are not doing the Phase 1–6 items yet:
logs/audit/trace/tuning/debugging


safety


memory (as a product feature layer)


realtime rails (as a product feature layer)


entitlements & subscriptions (full Stripe/product logic)


artifacts & lineage (full model)


Phase 0 only ensures the spine exists so those layers can be implemented cleanly and always on real infra.
