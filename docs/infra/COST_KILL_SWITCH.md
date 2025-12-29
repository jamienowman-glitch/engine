# Cost Kill-Switch + Azure Backstop

This document collects the runtime guardrails for Vertex billing and the Azure adapter contract.

## Vertex Billing Guard

- Vertex features are *denied by default*. Every path that reaches Vertex must call `ensure_billable_vertex_allowed(...)` before instantiating clients.
- Enable Vertex by setting `ALLOW_BILLABLE_VERTEX=1`; the guard raises `RuntimeError` pointing back to this document when unset.
- Guarded integrations include streaming (`engines/chat/service/llm_client.py`), Nexus embeddings, Vertex vector stores, and other outbound Vertex tooling.

## Azure Backstop Contract

### Azure Cosmos DB (memory)

The future Cosmos memory backend must honor:

- `AZURE_COSMOS_URI`
- `AZURE_COSMOS_KEY`
- `AZURE_COSMOS_DB`
- `AZURE_COSMOS_CONTAINER`

`AzureCosmosMemoryBackend` currently raises a clear error that references this doc until the integration is wired.

### Azure Blob Storage

The backstop storage adapter must honor:

- `AZURE_STORAGE_ACCOUNT`
- `AZURE_STORAGE_CONTAINER`
- `AZURE_STORAGE_KEY` (or SAS token)

`AzureBlobStorageAdapter` also fails fast and points back to this file so future wiring follows the exact env naming.

## Ops Status Visibility

- Use `GET /ops/status` or `python -m engines.ops.status` to examine the runtime configuration.
- Reported fields include the storage provider/target, memory backend, model provider, and whether `ALLOW_BILLABLE_VERTEX` is enabled.
- This endpoint gives visibility to non-terminal humans before executing Vertex workloads.
