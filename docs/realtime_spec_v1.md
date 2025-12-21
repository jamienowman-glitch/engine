
# NORTHSTAR REALTIME SPEC v1

Scope: Chat rail + Canvas (artifact) collaboration + Graft visible work + replay + audits/artifacts + tenancy isolation.
Rails: WebSocket + SSE are both first-class and mandatory.
Principle: Everything is an event. Events have stable IDs, routing keys, ordering, replay rules, and storage rules.

---

## 1) Canonical Routing Keys (no exceptions)

Every request, event, artifact, command, subscription must carry the full routing set.

**RoutingKeys v1**
* `tenant_id` (format `t_<slug>`, never “tenant-0” literal)
* `env` (`dev`|`staging`|`prod`|...)
* `workspace_id`
* `project_id`
* `app_id`
* `surface_id` (page/screen instance)
* `canvas_id` (artifact instance)
* `projection_id` (canvas view / inspector / tree / timeline etc.)
* `panel_id` (UI panel instance)
* `thread_id` (chat thread)
* `actor_id` (human user OR agent instance)
* `actor_type` (`human`|`agent`|`system`)
* `session_id` (client session)
* `device_id` (optional but supported)

**Hard rule:** Server validates that routing keys belong to tenant/env and that actor has membership. “Guessable IDs” never grant access.

---

## 2) Two Realtime Rails (both exist, both used)

### A) WebSocket rail (bi-di, low latency)

Used for:
* chat rail tokens + tool calls + tool results
* presence + “who’s editing what”
* live gesture events (optional routing; controlled by flags)
* run/step lifecycle events (optional streaming)

### B) SSE rail (one-way fanout + replay-friendly)

Used for:
* authoritative canvas commits (truth stream)
* artifact notifications (preview/audit/replay/export)
* optionally gestures (if you want gestures one-way fanout at scale)

**Hard rule:** Both rails share the same event envelope. Different transports, same contract.

---

## 3) Canonical Event Envelope (the actual contract)

This is the only shape the UI consumes. No ad-hoc “Message.text JSON maybe”.

**StreamEvent v1**

```json
{
  "v": 1,
  "type": "…",
  "ts": "RFC3339",
  "seq": 123456,
  "event_id": "ulid_or_uuid",
  "trace_id": "uuid",
  "span_id": "uuid",
  "ids": {
    "request_id": "uuid",
    "correlation_id": "uuid",
    "run_id": "uuid",
    "step_id": "uuid"
  },
  "routing": {
    "tenant_id": "t_*",
    "env": "dev",
    "workspace_id": "...",
    "project_id": "...",
    "app_id": "...",
    "surface_id": "...",
    "canvas_id": "...",
    "projection_id": "...",
    "panel_id": "...",
    "thread_id": "...",
    "actor_id": "...",
    "actor_type": "human|agent|system",
    "session_id": "...",
    "device_id": "..."
  },
  "data": {},
  "meta": {
    "schema": "optional",
    "priority": "truth|gesture|info",
    "persist": "always|sampled|never"
  }
}
```

**Event ordering**
* `seq` is monotonically increasing per stream key:
    * chat stream key: `(tenant_id, env, thread_id)`
    * canvas truth stream key: `(tenant_id, env, canvas_id)`
    * presence stream key: `(tenant_id, env, canvas_id)` or `(tenant_id, env, thread_id)` depending context
* `event_id` is globally unique (ULID preferred for sortability).

---

## 4) Mandatory Event Types (no debate)

**Run lifecycle (core/agents)**
* `run_start`
* `run_end`
* `step_start`
* `step_end`
* `error`

**Chat rail**
* `agent_message` (final text)
* `token_chunk` (streaming)
* `tool_call`
* `tool_result`

**Canvas truth (authoritative)**
* `canvas_commit` (ops batch committed, replayable)

**Graft live feel (ephemeral but recordable)**
* `canvas_gesture` (caret/selection/drag/scrub etc.)

**Artifacts**
* `artifact_written` (preview, audit, replay, export, media refs)
* `audit_result` (optional alias of artifact_written; but artifact_written must exist)

**Presence**
* `presence_state` (who’s editing what)
* `presence_ping` / heartbeat

---

## 5) “Visible Work” is not optional

Two streams per canvas
1. **Truth stream** (`canvas_commit`)
    * persisted, replayable, canonical history
2. **Gesture stream** (`canvas_gesture`)
    * makes it feel like hands are working
    * can be persisted sampled/keyframed for replay

**Hard rule:** No “spinner then replace page”. Everything is expressed as ops/gestures.

---

## 6) Commands + Revision Model (maximum proper)

This is the backbone for multi-user, multi-agent, multi-canvas consistency.

**CommandEnvelope v1**

```json
{
  "v": 1,
  "command_id": "uuid",
  "idempotency_key": "string",
  "base_rev": 41,
  "routing": { "...RoutingKeys" },
  "actor": { "actor_id": "...", "actor_type": "..." },
  "correlation_id": "uuid",
  "intent": {
    "label": "Fix hero CTA",
    "why": "Increase CTR for mobile",
    "origin": "human|agent",
    "policy_context": { "kpi": "...", "budget": "...", "temperature": "..." }
  },
  "ops": [ { "op": "...", "..." : "..." } ]
}
```

**Response rules**
* If `base_rev == head_rev`:
    * apply deterministically
    * increment head
    * emit `canvas_commit`
    * return `{head_rev, commit_id}`
* If mismatch:
    * return stable error:
        * code: `REV_MISMATCH`
        * `head_rev`
        * `since` cursor OR `ops_since_base` if available
        * `snapshot_ref` if buffer is insufficient

**Why this matters (bossman version)**

Multiple humans/agents edit at once. If you both edit based on old state, server must prevent silent corruption. You either:
* apply if you’re up to date, or
* tell you exactly how to catch up and retry.

---

## 7) Text correctness: range ops AND full set ops BOTH supported

You asked “what the fuck is range ops”.

Range ops = editing part of a text token

Instead of replacing the whole string, you send:
* insert characters at position
* delete a span
* replace a span

This is how you can visually show keystrokes and avoid stomping concurrent edits.

**Spec decision: support both:**
* `set_token` (full replace)
* `replace_text_range` / `insert_text` / `delete_range` (fine-grained)

But: if the goal is “visible typing”, the agent either:
* emits range ops directly, OR
* emits full change AND server/FE generates a “typing visualization plan” as gestures.
Both exist. Switchable in feature flags.

---

## 8) Replay (Graft playback) is first-class

You want:
* real-time visible work when watching
* fast replay when work happened in background (auto-mode)

**Replay artifact types**
* `replay_keyframes` (sampled gestures + commit checkpoints)
* `replay_full` (optional heavy; not required always)

**Replay generation rules**
* Interactive mode: capture more gesture detail
* Auto mode: capture keyframes + commit timestamps only
* Always allow “architect reveal” view:
    * sales narrative summary (human-friendly)
    * raw audit/debug log (legal/engineering)

These are two different artifacts:
* `walkthrough_sales`
* `walkthrough_debug`

---

## 9) Storage rules (maximum, clean, consistent)

**Binary/object storage**
* S3 is canonical for big/binary:
    * `media_v2` binaries
    * previews (html/images)
    * replay assets
    * exported bundles
    * audit bundles
    * Key prefixing is mandatory:
        * `tenants/{tenant_id}/{env}/...`

**Metadata registry**
* Firestore/Nexus backend stores:
    * artifact metadata
    * lineage (rev, correlation_id, upstream refs)
    * audit summaries
    * links to S3 URIs
    * `DatasetEvent`s for logging/training/debugging

**Artifact identity**

Every artifact has:
* `artifact_id`
* `kind`
* `uri` (S3)
* `routing` keys
* `rev` it corresponds to
* `correlation_id` that produced it
* `created_at`

---

## 10) CAP-001 bindings privacy (proper + safe)

You asked to explain “FE stores only binding_ref”.

**Meaning:**

Front-end should not receive or persist sensitive raw signals unless allowed.
So FE stores:
* the name/ref of the signal (“inventory.level”, “locale”, “utm_campaign”)
* a fallback value if signal is unavailable
Backend resolves:
* actual values
* applies privacy filtering/redaction
* logs exposures

**Spec decision:**
* FE can list signal names + metadata + privacy class
* FE can bind tokens to `binding_ref`
* Backend resolves at render/export/personalization runtime

---

## 11) Audits meaning (graph vs render vs both)

You asked what “audit on graph vs render” means.
* **Graph audit** checks structure without rendering:
    * layout constraints, overflow risk, invalid slot structure
* **Render audit** checks the actual output:
    * a11y (roles, contrast, labels)
    * perf (weight, CWV)
    * journey analysis (dead ends, nav complexity)

**Spec decision: do both.**
* layout solver validates graph
* a11y/perf/journey validate rendered preview artifact

---

## 12) Gates: what is gated and what isn’t

You challenged Strategy Lock vs KPI/budget/etc.

**Spec decision: editing is never gated.**

Canvas edits are always allowed (subject to auth + tenant).

**What gets gated:**

Anything that mutates the external world:
* publishing to Shopify/web/email provider
* posting to Instagram/Twitter/etc.
* spending money (ads)
* billing/subscription changes
* connector writes

**Gate policy is configurable:**
* Strategy Lock can be required OR bypassed if:
    * firearms/license ok
    * kill_switch ok
    * KPI corridors ok
    * budget ok (if budget is part of policy)
    * temperature ok
    * tenant has explicitly enabled auto mode

That policy is not in the canvas. It’s in the control plane + runtime.

---

## 13) Presence: “who’s editing what”

You asked “human or agent?”

**Answer: both.**

Presence is not just “users online”. It is:
* selected atom ids
* focused token path + caret range
* current gesture (dragging/scrubbing)
* actor identity (human/agent)
* last_seen timestamp

Presence must stream over WS (best) and can be mirrored to SSE if needed.

---

## 14) Transport endpoints (maximum set)

You’ll implement these shapes. Names can vary; contract doesn’t.

**WebSocket**
* `/ws/chat` (multiplexed, filters by routing keys)
* `/ws/presence` (multiplexed)
* optional `/ws/gestures` (if you keep gestures on WS)

**SSE**
* `/sse/canvas/commits` (multiplexed or per-canvas)
* `/sse/canvas/artifacts`
* optional `/sse/canvas/gestures` (if gestures on SSE)

All require auth + `RequestContext` + routing validation.

---

## 15) Backpressure + limits (must exist)

**Rules:**
* Hard max event size
* Bounded buffers per stream key
* Drop policy:
    * drop gestures first
    * never drop commits
* If client falls behind beyond buffer:
    * emit error: `REPLAY_MISS` + `snapshot_ref`

---

## 16) Cancellation (must exist, not global kill only)
* `POST /runs/{run_id}/cancel`
* emits `run_end` with `{cancelled:true}`
* pipeline checks cancellation between steps/chunks/tool calls

KillSwitch remains global emergency stop.
