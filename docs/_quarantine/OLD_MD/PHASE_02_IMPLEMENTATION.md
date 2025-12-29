# PHASE 2 IMPLEMENTATION PLAN

## Summary
Implement the "Atoms" layer: deterministic transformation of Raw Assets into derived artifacts (Atoms) with lineage tracking. This introduces `AtomArtifact` model, `AtomRepository` (interface + in-memory implementation initially/Firestore-stubbed), and `AtomService`. A new route `POST /nexus/atoms/from-raw` accepts a `raw_asset_id` and an operation type (e.g. `text_split_paragraph`), performs the operation deterministically, and stores the resulting atom metadata linked to the parent.

## User Review Required
> [!IMPORTANT]
> **Deterministic Logic**: The atomizer logic (splitting text, extracting frames) MUST be deterministic. We will start with a dummy "pass-through" or simple text splitter atomizer to validate the pipeline without complex media deps.

## Proposed Changes

### `engines/nexus`
#### [NEW] [models.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/atoms/models.py)
- `AtomArtifact` model:
  - `atom_id`: uuid (PK)
  - `tenant_id`: str (PK component)
  - `env`: str (PK component)
  - `parent_asset_id`: str (FK)
  - `uri`: str (optional, if atom is a file)
  - `content`: str (optional, for text atoms)
  - `op_type`: str (e.g. `text_identity`, `text_split`)
  - `op_version`: str
  - `source_start_ms`: int?
  - `source_end_ms`: int?
  - `metadata`: dict
  - `created_at`: datetime

#### [NEW] [repository.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/atoms/repository.py)
- `AtomRepository` protocol.
- `InMemoryAtomRepository` (for Phase 2 baseline).
- Methods: `create_atom`, `get_atom`.

#### [NEW] [service.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/atoms/service.py)
- `AtomService`:
  - `create_atom_from_raw(ctx, raw_asset_id, op_type, params)`
  - Logic:
    1. Fetch raw asset metadata (via RawAssetService or direct repo, need Interface).
    2. Perform deterministic Op (initially just `identity` or `mock`).
    3. Create Atom record.
    4. Emit `atom_created` DatasetEvent.

#### [NEW] [routes.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/atoms/routes.py)
- `POST /nexus/atoms/from-raw`:
  - Input: `{ raw_asset_id, op_type, params? }`
  - Output: `AtomArtifact`

### `engines/chat`
#### [MODIFY] [server.py](file:///Users/jaynowman/dev/northstar-engines/engines/chat/service/server.py)
- Mount `engines.nexus.atoms.routes.router`.

## Verification Plan

### Automated Tests
Create `engines/nexus/atoms/tests/test_atoms.py`:
- **Unit Tests**:
  - Verify `AtomArtifact` model.
  - Test `AtomService` logic (mocking `RawStorageRepository` or Service).
  - Test Lineage logging (DatasetEvent).
- **Integration Tests**:
  - `TestClient` call to `POST /nexus/atoms/from-raw`.
  - Verify valid Atom response.
  - Verify DatasetEvent emitted.

**Command**:
```bash
python -m pytest engines/nexus/atoms/tests/test_atoms.py
```

### Manual Verification
1. Run server: `uvicorn engines.chat.service.server:app`
2. Presign/Register a raw asset (reuse Phase 1 flow).
3. Call `POST /nexus/atoms/from-raw` with the new `raw_asset_id`.
4. Verify response contains `atom_id` and correct `parent_asset_id`.

### "No Prompts" Compliance
- Verify `service.py` contains no LLM calls or prompts.
- `grep` check.
