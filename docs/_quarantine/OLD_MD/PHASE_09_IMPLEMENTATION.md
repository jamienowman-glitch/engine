# PHASE 9 IMPLEMENTATION PLAN

## Summary
Implement "Production Hardening Checklist". This phase adds operational controls to Nexus engines:
1. **Kill Switch Integration**: Wire `KillSwitchService` into all public Nexus API routes to enable emergency disablement.
2. **Rate Limiting**: Add a basic in-memory rate limiter to prevent abuse (placeholder for Redis/Gateway layer).
3. **Quotas**: Add a skeletal quota service to check tenant usage limits.
4. **Verification**: Add a comprehensive hardening test suite ensuring tenancy isolation and control enforcement.

## User Review Required
> [!NOTE]
> **In-Memory Controls**: Rate limits and quotas will be in-memory for this phase (per process). This is sufficient for the "Engines" contract as defined in Phase 9 spec.
> **Kill Switch**: We will use the existing `engines/kill_switch` service but wire it effectively.

## Proposed Changes

### `engines/nexus/hardening` (New Module)
#### [NEW] `engines/nexus/hardening/rate_limit.py`
- `RateLimiter`: Simple class using `time` and `collections.deque` or token bucket to limit requests/sec per tenant.
- `check_rate_limit(ctx, action)`: Dependency to be used in routes.

#### [NEW] `engines/nexus/hardening/quotas.py`
- `QuotaService`: Stub service checking storage usage (mocked) vs limits.
- `check_quota(ctx, action)`: Dependency.

### `engines/nexus` (wiring)
#### [MODIFY] `engines/nexus/*/routes.py` (cards, index, packs, runs, memory, raw_storage, atoms)
- Update all `routes.py` to:
  - Import `KillSwitchService` and `HardeningService` (Rate/Quota).
  - Add dependencies to route functions:
    ```python
    def route(
        ...,
        kill_switch: KillSwitchService = Depends(get_kill_switch),
        rate_limit: None = Depends(check_rate_limit)
    ):
        kill_switch.ensure_action_allowed(ctx, "nexus_read")
        ...
    ```

## Verification Plan

### Automated Tests
Create `engines/nexus/hardening/tests/test_prod_gates.py`:
- **Kill Switch**: Enable kill switch for T1, verify T1 requests 403, T2 requests 200.
- **Rate Limit**: Spam requests, verify 429.
- **Tenancy**: Re-verify cross-tenant leakage is impossible (using service direct calls).

**Command**:
```bash
python -m pytest engines/nexus/hardening/tests/test_prod_gates.py
```

### Manual Verification
1. Set Kill Switch via code/script.
2. Hit API.
3. Verify Blocked.
