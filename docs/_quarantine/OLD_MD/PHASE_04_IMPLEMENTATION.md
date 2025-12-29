# PHASE 4 IMPLEMENTATION PLAN

## Summary
Implement the "Indexing" layer to enable search over Cards. This includes a `CardIndexService` that handles embedding (mocked for now) and upserting into a `VectorStore`. The `CardService` will be updated to trigger indexing upon card creation. A generic `POST /nexus/search` endpoint will be added to expose vector+filter search.

## User Review Required
> [!NOTE]
> **Mock Embeddings**: For Phase 4, we will use a deterministic "mock" embedding generator (e.g. hashing terms to vector) to ensure tests pass without needing a real embedding model or API key.
> **In-Memory Store**: We will use an `InMemoryVectorStore` as the backend.

## Proposed Changes

### `engines/nexus`
#### [NEW] `engines/nexus/index`
- **[NEW] [models.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/index/models.py)**:
  - `SearchResult`: card_id, score, snippet.
  - `SearchQuery`: text, filters (tenant_id/env implicit), top_k.

- **[NEW] [repository.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/index/repository.py)**:
  - `VectorStore` (Protocol): `upsert(id, vector, metadata)`, `search(query_vector, filters, k)`.
  - `InMemoryVectorStore`: Implements simple dot-product search over stored vectors.

- **[NEW] [service.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/index/service.py)**:
  - `CardIndexService`:
    - `index_card(ctx, card)`: Generates fake vector (deterministic hash of body), upserts to store.
    - `search(ctx, query_text, filters)`: Generates query vector, calls store, returns results.
    - **Tenancy**: Enforces `tenant_id` and `env` in all metadata filters and upserts.

- **[NEW] [routes.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/index/routes.py)**:
  - `POST /nexus/search`: `SearchQuery` -> `List[SearchResult]`.

#### modification to `engines/nexus/cards`
- **[MODIFY] [service.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/cards/service.py)**:
  - Inject `CardIndexService` (optional).
  - In `create_card`: call `index_service.index_card(card)` after success.

### `engines/chat`
#### [MODIFY] [server.py](file:///Users/jaynowman/dev/northstar-engines/engines/chat/service/server.py):
- Mount `engines.nexus.index.routes.router`.
- Wire `CardIndexService` into `CardService`? (Or just rely on default/singleton behavior for now if we aren't using strict DI container yet). *Correction*: `server.py` mostly just mounts routers. Dependencies are often instantiated inside `get_service` via imports. I will update `CardService` to import `CardIndexService` or `get_index_service` helper.

## Verification Plan

### Automated Tests
Create `engines/nexus/index/tests/test_index.py`:
- **Unit Tests**:
  - `InMemoryVectorStore`: Verify upsert and search recall (using mock vectors).
  - `CardIndexService`: Verify `index_card` calls store with correct metadata (tenant, env).
  - `CardService`: Verify creating a card *also* indexes it (integration).
- **Integration Tests**:
  - `TestClient`: `POST /nexus/cards` -> `POST /nexus/search` should find the card.

**Command**:
```bash
python -m pytest engines/nexus/index/tests/test_index.py
```

### Manual Verification
1. Run server.
2. Create `Card` (Type: KPI, Body: "Revenue is important").
3. Search `POST /nexus/search` (Query: "Revenue").
4. Verify Hit.
5. Create `Card` in *different* tenant.
6. Search original tenant. Verify *no* hit for new card (Isolation).
