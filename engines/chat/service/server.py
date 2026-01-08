"""Aggregate app for universal chat transports (PLAN-024)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from engines.chat.service.http_transport import app as http_app
from engines.chat.service.ws_transport import router as ws_router
from engines.chat.service.sse_transport import router as sse_router
from engines.chat.service import routes as chat_routes
from engines.bossman.routes import router as bossman_router
from engines.media.service.routes import router as media_router
from engines.media_v2.routes import router as media_v2_router
from engines.maybes.routes import router as maybes_router
from engines.nexus.vector_explorer.routes import router as vector_explorer_router
from engines.nexus.vector_explorer.ingest_routes import router as vector_ingest_router
from engines.nexus.raw_storage.routes import router as raw_storage_router
from engines.nexus.atoms.routes import router as atoms_router
from engines.canvas_commands import router as canvas_commands_router
from engines.nexus.cards.routes import router as cards_router
from engines.nexus.index.routes import router as index_router
from engines.nexus.packs.routes import router as pack_router
from engines.nexus.settings.routes import router as settings_router
from engines.nexus.runs.routes import router as runs_router
from engines.nexus.memory.routes import router as nexus_memory_router
from engines.identity.routes_keys import router as keys_router
from engines.identity.routes_auth import router as auth_router
from engines.identity.routes_analytics import router as analytics_router
from engines.identity.routes_control_plane import router as control_plane_router
from engines.identity.routes_ticket import router as ticket_router
from engines.strategy_lock.routes import (
    router as strategy_lock_router,
    policy_router as strategy_policy_router,
)
from engines.temperature.routes import router as temperature_router
from engines.video_timeline.routes import router as video_timeline_router
from engines.video_render.routes import router as video_render_router
from engines.video_360 import routes as video_360_routes
from engines.video_regions import routes as video_regions_routes
from engines.audio_service.routes import router as audio_service_router
from engines.video_mask import routes as video_mask_routes
from engines.video_multicam import routes as video_multicam_routes
from engines.video_visual_meta.routes import router as video_visual_meta_router
from engines.audio_semantic_timeline.routes import router as audio_semantic_router
from engines.actions.router import router as actions_router
from engines.audio_voice_enhance.routes import router as audio_voice_enhance_router
from engines.video_presets import routes as video_presets_routes
from engines.video_text import routes as video_text_routes
from engines.budget.routes import router as budget_router
from engines.kpi.routes import router as kpi_router
from engines.seo.routes import router as seo_router
from engines.billing.routes import router as billing_router
from engines.debug.aws_routes import router as aws_debug_router
from engines.analytics_events.routes import router as analytics_events_router
from engines.three_wise.routes import router as three_wise_router
from engines.firearms.routes import router as firearms_router
from engines.memory.routes import router as memory_router
from engines.kill_switch.routes import router as kill_switch_router
from engines.knowledge.routes import router as knowledge_router
from engines.ops.status import router as ops_status_router
from engines.origin_snippets.routes import router as origin_snippets_router
from engines.persistence.routes import router as persistence_router
from engines.routing.routes import router as routing_router
from engines.config_store.routes import router as config_store_router
from engines.registry.routes import router as registry_router

from engines.routing.manager import startup_validation_check


def create_app() -> FastAPI:
    app = http_app
    
    # Haze FPV / Mobile Support: allow CORS from any LAN IP
    if not getattr(app.state, "northstar_cors_added", False):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        app.state.northstar_cors_added = True
    
    if not getattr(app.state, "northstar_routes_added", False):
        # P0 Phase 0 Closeout: Validate routing configuration before mounting services
        # This ensures fail-fast behavior if required services are not properly configured
        startup_validation_check()
        
        app.include_router(ws_router)
        app.include_router(sse_router)
        app.include_router(chat_routes.router)
        app.include_router(media_router)
        app.include_router(media_v2_router)
        app.include_router(maybes_router, tags=["maybes"])
        app.include_router(auth_router)
        app.include_router(keys_router)
        app.include_router(analytics_router)
        app.include_router(control_plane_router)
        app.include_router(ticket_router)
        app.include_router(strategy_lock_router)
        app.include_router(strategy_policy_router)
        app.include_router(temperature_router)
        app.include_router(vector_explorer_router)
        app.include_router(vector_ingest_router)
        app.include_router(video_timeline_router)
        app.include_router(video_render_router)
        app.include_router(video_360_routes.router)
        app.include_router(video_regions_routes.router)
        app.include_router(audio_service_router)
        app.include_router(video_mask_routes.router)
        app.include_router(video_multicam_routes.router)
        app.include_router(video_visual_meta_router)
        app.include_router(audio_semantic_router)
        app.include_router(audio_voice_enhance_router)
        app.include_router(video_presets_routes.router)
        app.include_router(video_text_routes.router)
        app.include_router(budget_router)
        app.include_router(billing_router)
        app.include_router(kpi_router)
        app.include_router(seo_router)
        app.include_router(bossman_router)
        app.include_router(aws_debug_router)
        app.include_router(kill_switch_router)
        app.include_router(ops_status_router)
        app.include_router(knowledge_router)
        app.include_router(analytics_events_router)
        app.include_router(three_wise_router)
        app.include_router(firearms_router)
        app.include_router(memory_router)
        app.include_router(actions_router)
        app.include_router(raw_storage_router)
        app.include_router(atoms_router)
        app.include_router(cards_router)
        app.include_router(index_router)
        app.include_router(pack_router)
        app.include_router(settings_router)
        app.include_router(runs_router)
        app.include_router(nexus_memory_router)
        app.include_router(canvas_commands_router)
        app.include_router(origin_snippets_router)
        app.include_router(persistence_router)
        app.include_router(routing_router)
        # L1-T2 mounts
        from engines.canvas_stream.router import router as canvas_stream_router
        from engines.feature_flags.routes import router as feature_flags_router
        app.include_router(canvas_stream_router)
        app.include_router(feature_flags_router)
        app.include_router(config_store_router)
        app.include_router(registry_router)
        app.state.northstar_routes_added = True
    return app


app = create_app()
