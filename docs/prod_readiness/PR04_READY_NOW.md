The following engines are closest to ready for UI/agents usage today (caveats noted):

- chat_service — Identity enforced and error handlers exist; needs durable store and replay plus observability to be fully compliant.
- media_v2_assets — Identity enforced and artifact registry works; requires error envelope, enforced durable backends, and meta/budget fixes.
- vector_explorer — Identity enforced and strategy_lock on ingest; needs error envelope and observability.
- video_render — Identity enforced and rich service implementation; needs pipeline_hash meta, error envelope, and budget/audit.
- video_timeline — Identity enforced with Firestore repo; must add error envelope and config guard.
- raw_storage — Identity + GateChain on presign/register; needs error envelope and stricter backend enforcement.

Everything else (canvas_stream, audio_service, audio_semantic_timeline, video_regions, cad_ingest, image_core, scene_engine, marketing_cadence, budget_usage) requires identity/error/durability work before being “ready now.”
