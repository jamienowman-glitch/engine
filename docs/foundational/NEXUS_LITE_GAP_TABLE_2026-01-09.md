# Nexus Lite Gap Table

**Date:** 2026-01-09
**Status:** GAP ANALYSIS

| ID | Requirement | Status | Evidence (Path) | Owner | Risk | Minimal Implementation |
|---|---|---|---|---|---|---|
| **G1** | **LanceDB Library** | **NO** | `pyproject.toml` (missing dependency) | Engines | **P0** | Add `lancedb` to dependencies. |
| **G2** | **Fsspec Storage** | **NO** | `engines/storage` (missing fsspec) | Engines | **P0** | Add `fsspec`, `s3fs`, `gcsfs`. Refactor storage access. |
| **G3** | **Lance Vector Configuration** | **NO** | `engines/routing/registry.py` (missing backend type) | Engines | **P0** | Add `NEXUS_LITE` backend support to routing registry. |
| **G4** | **Nexus Lance Store** | **NO** | `engines/nexus/lance_store.py` (FILE MISSING) | Engines | **P0** | Implement `NexusVectorStore` using LanceDB. |
| **G5** | **Ingest Worker** | **NO** | `engines/nexus/worker.py` (FILE MISSING) | Engines | **P0** | Event Listener: `nexus.ingest` -> Write to Lance. |
| **G6** | **Nexus Service (Lite)** | **PARTIAL** | `engines/nexus/rag_service.py` | Engines | P1 | Update service to look up `nexus_store` route. |
| **G7** | **Global Query Fusion** | **NO** | `engines/nexus/rag_service.py` | Engines | P1 | Logic to query Tenant + Global stores and merge hits. |
| **G8** | **KPI Fact Generator** | **NO** | `engines/kpi` (raw data only) | Engines | P2 | Worker: Read `raw.jsonl` -> Summarize -> Emit Ingest Event. |
| **G9** | **HAZE Adapter** | **PARTIAL** | `engines/nexus/vector_explorer` (Vertex only) | Engines | P2 | Abstract `VertexExplorer` -> `VectorExplorer` protocol. |
| **G10**| **UI Connection** | **NO** | `agentflow/components/haze` (Mock/Static) | UI | P2 | update endpoint urls in React components. |

## Notes
*   **P0 items** must be completed to unblock basic MCP ingestion.
*   **Event Spine** is the chosen async mechanism (reuse existing `engines/event_spine`).
