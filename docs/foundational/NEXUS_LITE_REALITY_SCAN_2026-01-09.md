# Nexus Lite Reality Scan

**Date:** 2026-01-09
**Status:** COMPLETE
**Scope:** /northstar-engines, /northstar-agents, /ui

## 1. Existing Nexus & Vector Infrastructure

### **Nexus Core (`engines/nexus`)**
*   **Status:** PARTIAL
*   **Evidence:**
    *   `engines/nexus/vector_store.py`: Contains `VertexVectorStore` implementation (hardcoded to Vertex AI).
    *   `engines/nexus/schemas.py`: Defines `NexusEmbedding`, `NexusKind`.
    *   `engines/nexus/rag_service.py`: Service layer exists but likely wired to Vertex.
*   **Verdict:** Existing interfaces can be reused, but the backing store must be swappable. `LanceVectorStore` is **MISSING**.

### **HAZE / Vector Explorer (`engines/nexus/vector_explorer`)**
*   **Status:** PARTIAL (Vertex Native)
*   **Evidence:**
    *   `engines/nexus/vector_explorer/vector_store.py`: Coupled to Vertex Matching Engine.
    *   `engines/nexus/vector_explorer/tests/test_vertex_smoke.py`: Smoke tests require GCP creds.
    *   `agentflow/components/haze/HazeViewer.tsx`: Front-end viewer exists.
*   **Verdict:** HAZE exists but is not compatible with local/offline usage. Needs abstraction to run on LanceDB.

## 2. Storage & Media

### **Blob Storage**
*   **Status:** MISSING (Standardized Abstraction)
*   **Evidence:**
    *   `engines/storage/gcs_client.py`: Raw GCS client.
    *   `engines/storage/filesystem_tabular.py`: Local file handling.
    *   **Search:** `fsspec` keyword yielded **0 results**.
*   **Verdict:** `fsspec` is **MISSING**. This is a critical gap for portable "Lite" mode (allowing S3/Az/GCS/Local via one API).

## 3. KPI Subsystem

### **KPI Storage (`engines/kpi`)**
*   **Status:** EXISTS (File/InMemory)
*   **Evidence:**
    *   `engines/kpi/repository.py`: Supports `FileKpiRepository` (writes to `var/kpi/.../raw.jsonl`).
    *   `engines/kpi/models.py`: Defines `KpiRawMeasurement`.
*   **Summarization:**
    *   **Verdict:** **MISSING**. No worker exists to transform raw JSONL measurements into "Fact Docs" (text summaries) for RAG.

## 4. Async & Routing Patterns

### **Routing (`engines/routing`)**
*   **Status:** CONFIRMED
*   **Evidence:**
    *   `engines/routing/registry.py`: `ResourceRoute` model supports tenant/env isolation.
    *   `engines/common/error_envelope.py`: Canonical error structure (`missing_route_error`) exists.

### **Async / Event Spine (`engines/event_spine`)**
*   **Status:** CONFIRMED
*   **Evidence:**
    *   `engines/event_spine/service.py`: Exists.
    *   `engines/persistence/events.py`: Event models.
*   **Verdict:** Can use `event_spine` for "Ingest Requested" events, consumed by a worker. No heavy Celery/Redis queue found, so sticking to Event Spine + simple worker is the correct "Lite" architecture.

## 5. What We Can Reuse
*   **Identity:** `engines.common.identity.RequestContext` (Strict tenant isolation).
*   **Errors:** `engines.common.error_envelope` (Standard 410/503 responses).
*   **Interfaces:** `NexusVectorStore` protocol in `nexus/vector_store.py`.
