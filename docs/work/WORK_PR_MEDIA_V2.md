# Media V2 Hardening Work Log

## Summary
- Wire the media_v2 router to canonical `ErrorEnvelope` responses so every HTTPException is normalized (validation, auth, and business guards all emit `error` objects).
- Guard every media_v2 route in sellable modes to ensure `RAW_BUCKET` + Firestore config are present, and only allow a lab-local fallback when `MEDIA_V2_ALLOW_LOCAL_STORAGE=1`.
- Stamp every derived artifact with a deterministic `pipeline_hash` plus an explicit `backend_version` so downstream tooling can detect idempotent outputs.

## Tests
- `pytest engines/muscle/media_v2/tests/test_media_v2_endpoints.py`

## Manual verification
1. For lab-style smoke testing, export `MEDIA_V2_ALLOW_LOCAL_STORAGE=1` (the default in the tests) and issue a request with locally minted JWT headers:
   ```sh
   TOKEN=$(python - <<'PY'
   from engines.identity.jwt_service import default_jwt_service
   svc = default_jwt_service()
   claims = {
      "sub": "user-1",
      "default_tenant_id": "t_demo",
      "tenant_ids": ["t_demo"],
      "role_map": {"t_demo": "member"},
   }
   print(svc.issue_token(claims))
   PY)
   ```
   Then `curl` a multipart upload with the canonical headers (`X-Tenant-Id`, `X-Mode: lab`, `X-Project-Id`, `Authorization`) with `ENV=dev` in your shell and confirm the JSON response contains `artifact.meta.pipeline_hash` + `artifact.meta.backend_version`.
2. To verify the error envelope in prod modes, drop `RAW_BUCKET`/`GCP_PROJECT` from the environment, hit `/media-v2/assets` in `X-Mode: saas`, and assert you receive `error.code == "media_v2.raw_bucket_missing"` and `error.http_status == 500`.
3. Artifact metadata can be inspected via `curl /media-v2/assets/{asset_id}` and looking at `artifacts[].meta`; the new pipeline hash should match across deployments that submit the same `ArtifactCreateRequest` (see the unit test for how deterministic requests behave).
