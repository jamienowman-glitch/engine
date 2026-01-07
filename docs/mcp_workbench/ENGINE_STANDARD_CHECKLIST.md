# ENGINE STANDARD CHECKLIST

## 1. Identity Enforcement
- **Requirement**: All internal routes MUST enforce `RequestContext` dependency.
- **Verification**: 
    - Function signature must include `ctx: RequestContext = Depends(get_request_context)`.
    - Headers `X-Tenant-Id`, `X-Mode`, `X-Project-Id` (optional) must be propagated.
- **Exception**: Public/Read-Only routes explicitly documented in Matrix.

## 2. Canonical Error Envelope
- **Requirement**: All errors MUST return `ErrorEnvelope`.
- **Verification**:
    - No bare `HTTPException` without envelope structure.
    - `POST` / `PUT` / mutation endpoints should return `Envelope[T]`.
    - Validation errors must be caught and wrapped.

## 3. Routing & Durability Guardrails
- **Requirement**: In `sellable` modes (non-dev), NO silent filesystem/in-memory fallbacks.
- **Verification**:
    - Check for `if mode == "prod": use_s3()` logic.
    - Check that missing backends (e.g. Redis, S3) cause Canonical Errors, not crashes.

## 4. GateChain for Safe Mutations
- **Requirement**: All mutating operations (CREATE, UPDATE, DELETE) must use `GateChain`.
- **Verification**:
    - Look for `GateChain.run(...)` or equivalent policy enforcement.
    - No direct DB writes without a policy check.
    - Exception: Strictly "My Data" scoped routes where ownership is validated by Identity alone.

## 5. Streaming Semantics
- **Requirement**: SSE/WS endpoints must use proper cursors and connection management.
- **Verification**:
    - `cursor` param present.
    - Connection lifecycles managed (heartbeats, disconnect handling).
