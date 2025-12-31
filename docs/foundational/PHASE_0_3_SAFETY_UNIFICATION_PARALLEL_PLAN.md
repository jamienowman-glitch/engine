# Phase 0.3 — Safety Unification Parallel Plan (Docs-Only)

## Worker splits
### 2 workers
- Worker A: Lane 1 (RequestContext + X-Mode), then Lane 4 (Budget policy).  
- Worker B: Lane 2 (GateChain on chat/canvas) + Lane 3 (timeline + SAFETY_DECISION), after Lane 1 is in and coordinating with Lane 4 readiness.

### 3 workers
- Worker A: Lane 1 (RequestContext + X-Mode).  
- Worker B: Lane 4 (Budget policy persistence + API).  
- Worker C: Lane 2 + Lane 3 (GateChain insertion, timeline + SAFETY_DECISION) once Lane 1 is merged; coordinate with Worker B for budget enforcement switch-off from env.

## Dependency graph (must respect)
- Lane 1 → Lane 2 and Lane 3 (context/mode required before gating/timeline).  
- Lane 4 → GateChain budget enforcement (Lane 2/3) to remove env thresholds.  
- Lane 2 and Lane 3 can develop in tandem after Lane 1; budget-related parts wait for Lane 4.  
- UI/Agents (Lanes 5/6, out-of-repo) start after Engine surfaces stable.

## Ordered commit sequence (main branch)
1) `engines: enforce X-Mode in RequestContext` (Lane 1)  
2) `engines: persisted budget policy and gate enforcement` (Lane 4)  
3) `engines: GateChain on chat and canvas actions` (Lane 2)  
4) `engines: safety decisions appended to timeline and canvas replay` (Lane 3)  
- UI/Agents commits happen in their repos after the above land.

## Coordination checkpoints
- After Lane 1 merge: confirm headers/mode contract stable.  
- After Lane 4 merge: confirm env thresholds removed; policy API available.  
- After Lane 2/3 merge: end-to-end replay + safety decision visibility validated.
