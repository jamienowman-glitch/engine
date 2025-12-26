	1.	One-page overview
•	Goal: Bring every router mounted in server.py:create_app() into compliance with the Lane 2 guard contract: each protected endpoint must build RequestContext (with required project_id), get AuthContext, enforce tenant membership, and assert tenant/env/project matches before mutations. Add/adjust only plumbing + minimal guard tests; no business logic changes.
•	Guard contract:
•	Missing/invalid auth → 401
•	Auth ok but not a member of tenant → 403
•	Missing tenant/env/project in resolved context OR mismatch vs payload/query/path → 400
•	project_id is mandatory (header/query/body) via get_request_context.
•	Definition of Done: All mounted routers’ endpoints use get_request_context + get_auth_context, call require_tenant_membership, call assert_context_matches(…, project_id=request_context.project_id) where caller supplies tenant/env/project, and have passing guard tests (400/401/403) or are explicitly documented as intentionally public with tests.
	2.	Canonical patch pattern (templates)
•	Route signature pattern:from fastapi import Depends
•	from engines.common.identity import RequestContext, get_request_context, assert_context_matches
•	from engines.identity.auth import AuthContext, get_auth_context, require_tenant_membership
•
•	@router.post(”/path”)
•	def handler(
•	    payload: PayloadModel,
•	    request_context: RequestContext = Depends(get_request_context),
•	    auth_context: AuthContext = Depends(get_auth_context),
•	):
•	    require_tenant_membership(auth_context, request_context.tenant_id)
•	    assert_context_matches(
•	        request_context,
•	        tenant_id=payload.tenant_id,  # or query/path param if present; else None
•	        env=payload.env if hasattr(payload, “env”) else None,
•	        project_id=request_context.project_id,
•	    )
•	    # existing business logic unchanged
•
•	Placement:
•	require_tenant_membership(…) near the top, before any work or data access.
•	assert_context_matches(…) immediately after, only if the request includes tenant/env/project fields (body/query/path). If no such fields, skip or pass None for those args.
•	GET routes without body:
•	Always require RequestContext + AuthContext + require_tenant_membership.
•	If tenant/env/project appear as query/path params, call assert_context_matches with those values; otherwise, skip.
•	Routes bypassing dependencies:
•	Add request_context: RequestContext = Depends(get_request_context) and auth_context: AuthContext = Depends(get_auth_context) to the signature; then add require_tenant_membership and assert_context_matches as above.
•	If truly public, add # INTENTIONALLY_PUBLIC:  and a test proving safe/public behavior.
	3.	Router inventory (mounted in create_app) For each: path, rough endpoints, status, tests.
•	ws/sse transports (ws_transport.py, sse_transport.py): RED – streaming; ensure context/auth/membership checks; tests: test_sse_transport.py, test_sse_transport.py.
•	media (routes.py): YELLOW/RED – verify; tests likely under engines/media/tests (check existing).
•	media_v2 (routes.py): GREEN (already updated) – tests: test_media_v2_endpoints.py.
•	maybes (routes.py): YELLOW – check guards per endpoint; tests: engines/maybes/tests.
•	identity (auth/keys/analytics) (routes_auth.py, routes_keys.py, routes_analytics.py): likely GREEN; minimal confirm; tests: engines/identity/tests.
•	strategy_lock (routes.py): YELLOW – confirm membership per endpoint; tests: engines/strategy_lock/tests.
•	temperature (routes.py): YELLOW – confirm guards; tests: test_temperature_service_root.py, test_temperature_service_metrics.py.
•	video_timeline (routes.py): RED – currently lacks dependencies; tests: engines/video_timeline/tests.
•	video_render (routes.py): YELLOW/RED – confirm; tests: engines/video_render/tests.
•	video_360 (routes.py): YELLOW/RED – confirm; tests: engines/video_360/tests.
•	video_regions (routes.py): YELLOW – confirm; tests: engines/video_regions/tests.
•	audio_service (routes.py): YELLOW – confirm; tests: check engines/audio_service/tests.
•	video_mask (routes.py): YELLOW – confirm; tests: check engines/video_mask/tests.
•	video_multicam (routes.py): YELLOW – confirm; tests: engines/video_multicam/tests.
•	video_visual_meta (routes.py): YELLOW – confirm; tests: engines/video_visual_meta/tests.
•	audio_semantic_timeline (routes.py): YELLOW – confirm; tests: engines/audio_semantic_timeline/tests.
•	audio_voice_enhance (routes.py): YELLOW – confirm; tests: engines/audio_voice_enhance/tests.
•	video_presets (routes.py): YELLOW – confirm; tests: engines/video_presets/tests.
•	video_text (routes.py): YELLOW/RED – confirm; tests: check engines/video_text/tests.
•	budget (routes.py): likely GREEN; verify; tests
