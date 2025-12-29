North Star: One Graph, Many Lenses
The Core Idea
We are building one canonical execution graph (“Agent Flow”) that is the source of truth for what runs, in what order, with what inputs/outputs, and what gets logged.
Everything else is a lens/overlay on that same graph.
FlowGraph = nodes + edges + execution semantics (the truth)


Lenses = different views and bindings keyed to that same truth (UI, Safety, Engines/Connectors, Nexus, Budget, etc.)


If the graph is correct, every lens stays consistent. If a lens exists without graph truth, you get drift and chaos.
Atomic Building Blocks (Mix-and-Match)
Everything is split to maximum atomicity so you can swap pieces without rewriting everything:
PersonaCard: voice, principles, style, policies (identity only)


TaskCard: goal, constraints, acceptance criteria (job only)


ArtifactSpecCard: what gets produced, format, constraints, viewer hints


ModelCard: provider/model deployment, API surface, limits, streaming


CapabilityCard: a capability concept (vision, tool_use, web_grounding, etc.)


CapabilityBindingCard: how a capability toggles for a specific (provider, model)


Tool/Engine Cards (later): connectors + “muscle engines” (timeline render, publish, upload, etc.)


NodeCard: where composition happens (references to persona/task/model/caps/tools + blackboard IO)


FlowCard: nodes + edges + entry/exit + defaults/contracts


(Later) AppCard: a bundle of flows + surface bindings (an “app” is multiple graphs)


Key rule: Persona ≠ Task ≠ Model ≠ Capabilities ≠ Tools.
Nodes assemble them; flows wire nodes.
The Canonical Execution Substrate
What “Agent Flow” actually is
Agent Flow is the execution graph:
Nodes: “what runs here”


Edges: “what happens next”


IO: explicit blackboard reads/writes + artifact lineage


Runtime binding: which model/provider/capabilities/tools are available at that node


Trace: every run produces a structured trace + artifacts (nothing disappears)


Non-negotiables
No silent defaults for provider/model in real runs.


No SKIP in anything that claims to verify correctness; only PASS/FAIL.


Budget guardrails for live calls (token caps, timeouts, 1-call certification modes).


Deterministic auditability: you can always answer “what ran, why, using what, and what it wrote.”


The “Many Lenses” Concept (Same Graph, Different Overlays)
You can flip the same graph between lenses using a selector (like your mockup: “AGENTFLOW ▼”):
1) Agent Lens (Execution / Intelligence)
This is the “mother lens.”
Click a node → inspector shows resolved:
persona + task + model + capabilities + tools


blackboard read/write keys


artifact outputs


why resolution happened (overrides, defaults, policy)


This lens must support:
Run Node (in isolation)


Run Flow


Render Run (show status on the graph)


Live certification (prove model connectivity cheaply + safely)


2) UI Lens (Collaborative Canvases per Node)
The UI lens maps the same node_ids to:
Surface type for that node (builder, timeline editor, chat pane, inspector, etc.)


Panel bindings (what artifacts render where)


Interaction contract (what the human can edit vs view-only)


Mobile/desktop layout variants (horizontal desktop / vertical mobile)


So a node can “own” a UI canvas:
Website builder canvas


Email builder canvas


Timeline canvas (CapCut-like)


Gantt/planner canvas


Chat rail canvas


KPI / HITL approval canvas


Same flow, different UI experiences per node.
3) Safety / Policy Lens (Per Tenant + Per Node)
This lens overlays:
required checks (preflight, policy gates, red-team checks)


“three wise LLM” reviews (cold safety checkers)


firearm/license constraints, or other tenant-specific controls


policy outcomes written as artifacts + trace events (auditable)


Nothing magical: it’s still node-level wiring, just a different overlay.
4) Engines + Connectors Lens (Muscle + Delivery)
This lens maps nodes to:
internal “muscle engines” (render video, generate assets, compile timelines)


connectors (Shopify publish, YouTube upload, CRM writeback, etc.)


async semantics (start/poll/cancel/resume)


artifact kinds produced by engines


Engines/connectors behave like tools, but heavyweight tools with job semantics.
5) Nexus / Memory Lens (Knowledge + Retrieval)
This lens overlays:
which node reads from Nexus (RAG, entity graph pulls)


which node writes back (new facts, decisions, preferences)


scoping rules (tenant/global/user/team)


“strategy lock” anchors that must remain stable across runs


Again: node-level overlays keyed by node_id, not hidden global state.
Why This Structure Solves the “Unification Problem”
You’ve been building multiple canvases (website builder, timeline, CRM, etc.) and the hard part is: how do they all stay consistent?
Answer: they don’t unify at the UI level.
They unify at the graph + overlay binding level:
The graph is stable truth.


Lenses are bindings to that truth.


You can add new lenses later (3D lens, VR lens, analytics lens) without rewriting execution.


This is how we avoid drift and “nested folder mush” in code and in product.
The Endgame Workflow (How You’ll Actually Use It)
In chat: “I want a flow that does X.”


The system proposes a draft graph (nodes/edges + references).


You open the collaborative canvas (Agent Flow lens):


drag/drop nodes


attach persona/task/model/caps/tools


wire blackboards + artifacts


You click Validate:


PASS/FAIL report per node (machine-readable)


You click Run Node to test pieces:


see artifacts + trace


You click Run Flow to test end-to-end:


see live status on graph


You save it:


becomes a reusable flow template / app building block


Later:


bundle multiple flows into an AppCard


bind them to UI surfaces


connect Nexus, safety, engines, connectors per tenant


Development begins after the graph exists: debugging traces, improving personas/tasks, tightening capabilities, wiring engines/connectors, and iterating with complete visibility.
What We’re Building Toward Next (Practical Milestones)
Authoring: full drag/drop graph editor backed by safe registry/workspace writes


Inspection: click node → resolved everything, plus “why”


Validation: one JSON report the UI can render (PASS/FAIL per node)


Execution: run node / run flow / trace / render-run


Overlays: UI lens + safety lens + engines/connectors + Nexus lens


Bundling: flows → apps → surfaces


The One Sentence North Star
A single, auditable execution graph that can be viewed and edited through multiple lenses (Agent/UI/Safety/Engines/Nexus), where every node is mix-and-match from atomic cards, and every run produces complete traces and artifacts—so building apps becomes designing graphs, not writing fragile glue code.
“Frozen” Flows, But Not Deterministic Apps
Once a flow graph is authored and validated, we freeze it as a versioned template (think: flow.website_builder_v3). Frozen means:
The structure is stable: nodes/edges/contracts don’t silently mutate.


The bindings are explicit: which personas/tasks/models/capabilities/tools are attached at each node is recorded.


The audit surface is stable: the same flow version always produces the same kind of trace + artifacts.


But it is not a deterministic program.
Why it’s not deterministic
Every node can be backed by:
LLM calls (with capability toggles, tools, multi-turn frameworks)


Nexus retrieval (RAG / knowledge graph pulls that change over time)


Tenant-specific overlays (policy rules, safety gates, budgets, connector permissions)


Human-in-the-loop steps (approval/edits that alter downstream context)


So what’s “frozen” is the contract + structure + wiring, not the exact outputs.
“Frozen” = reproducible intent, not identical output
We freeze:
what the node is supposed to do (Task + acceptance criteria)


what identity it runs as (Persona)


what it’s allowed to use (Capabilities/Tools)


what it reads/writes (Blackboard + Artifact specs)


what model/provider policy applies (Model binding + resolution rules)


We don’t freeze:
the exact text the model produces


the exact retrieved facts (unless explicitly cached/versioned)


the exact decisions (because agent reasoning is probabilistic)


From Flows to Apps
An App later becomes:
a bundle of multiple flow graphs (each with multiple lenses)


shared surfaces (UI screens/panels)


shared tenant overlays (Nexus, safety, engines/connectors)


shared observability (one place to inspect every artifact + trace)


So:
Flow templates are the stable, composable building blocks.


Apps are collections of those blocks, wired to UI surfaces and tenant policies.


The whole system remains agentic at every node, not a deterministic workflow engine wearing an LLM costume.



