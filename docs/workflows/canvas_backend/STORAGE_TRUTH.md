# Storage Truth: Tenant Isolation & Pathing

**Status:** Enforced
**Changes:** Phase 3 (Steps 7-8)

## 1. Pathing Contract
All raw storage artifacts MUST follow the strict `REALTIME_SPEC_V1` pathing to ensure multi-tenant isolation at the bucket level.

### Format
`gs://{bucket}/tenants/{tenant_id}/{env}/{type}/{asset_id}/{filename}`

### Components
*   **tenant_id**: `t_[a-z0-9_-]+` (Validated by `RoutingKeys`)
*   **env**: `dev` | `staging` | `prod` (Inferred from deployment or context)
*   **type**: `media` | `datasets` | `raw` | `artifacts`

## 2. Enforced Code Paths

### Logic: `engines.storage.gcs_client`
The `GcsClient` methods have been hardened to strictly enforce prefixes:

```python
def upload_raw_media(self, tenant_id, path, content, env="dev"):
    # Enforced Prefix
    key = f"tenants/{tenant_id}/{env}/media/{path}"
    ...
```

### Verification
Tests in `engines/storage/tests/test_paths.py` verify that clients cannot write to root or cross-tenant paths accidentally.

## 3. Migration Note
Legacy data stored at `/{tenant_id}/media/...` is NOT automatically migrated. A migration script `scripts/migrate_storage_v1.py` will be required for any pre-existing production data (currently assumed empty/dev).
