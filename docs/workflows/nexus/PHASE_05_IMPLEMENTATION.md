# PHASE 5 IMPLEMENTATION PLAN

## Summary
Implement "Influence Packs": bundled sets of cards retrieved based on a query, providing provenance/lineage for downstream consumers. This phase introduces the `InfluencePack` model, `PackService` (which orchestrates search via `CardIndexService`), and the API endpoint `POST /nexus/influence-pack`.

## User Review Required
> [!IMPORTANT]
> **Clarification - Engines are Opaque**: Engines do not own, author, or interpret card content. Influence Packs are strictly containers of *references* (IDs, scores, artifact_refs) retrieved from the index.
> **Excerpts**: Excerpts are optional, non-semantic, opaque text blobs included solely for debugging/tooling. No summarization or semantic processing.

## Proposed Changes

### `engines/nexus`
#### [NEW] `engines/nexus/packs`
- **[NEW] [models.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/packs/models.py)**:
  - `CardRef`: card_id, score, excerpt (optional, opaque debug string), artifact_refs.
  - `InfluencePack`: pack_id, tenant_id, env, query, filters, card_refs, created_at.

- **[NEW] [service.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/packs/service.py)**:
  - `PackService`:
    - `create_pack(ctx, query, filters)`:
      1. Calls `CardIndexService.search(query)`.
      2. Maps results to `CardRef`s.
      3. **Logic**: Simply wraps the IDs/scores returned by the index. Excerpt is just `result.snippet` (if available from index) passed through opaquely.
      4. Creates `InfluencePack` object.
      5. Logs `pack_created` event.

- **[NEW] [routes.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/packs/routes.py)**:
  - `POST /nexus/influence-pack`: `SearchQuery` -> `InfluencePack`.

### `engines/chat`
#### [MODIFY] [server.py](file:///Users/jaynowman/dev/northstar-engines/engines/chat/service/server.py):
- Mount `engines.nexus.packs.routes.router`.

## Verification Plan

### Automated Tests
Create `engines/nexus/packs/tests/test_packs.py`:
- **Unit/Integration Tests**:
  - Mock `CardIndexService` to return fixed results (IDs/Scores).
  - Verify `PackService` wraps them into `InfluencePack` correctly.
  - Verify no semantic processing happens (input -> output pass-through).
  - Verify `tenant_id` propagation.

**Command**:
```bash
python -m pytest engines/nexus/packs/tests/test_packs.py
```

### Manual Verification
1. Run server.
2. Use `POST /nexus/search` to confirm hits (IDs) exist.
3. Call `POST /nexus/influence-pack` with same query.
4. Verify response is an `InfluencePack` containing the expected card IDs and scores.
