
import os
import sys

ROUTERS = {
    "engines.chat.service.ws_transport": "engines/chat/service/ws_transport.py",
    "engines.chat.service.sse_transport": "engines/chat/service/sse_transport.py",
    "engines.chat.service.routes": "engines/chat/service/routes.py",
    "engines.media.service.routes": "engines/muscle/media/service/routes.py",
    "engines.media_v2.routes": "engines/muscle/media_v2/routes.py",
    "engines.maybes.routes": "engines/maybes/routes.py",
    "engines.identity.routes_auth": "engines/identity/routes_auth.py",
    "engines.identity.routes_keys": "engines/identity/routes_keys.py",
    "engines.identity.routes_analytics": "engines/identity/routes_analytics.py",
    "engines.identity.routes_control_plane": "engines/identity/routes_control_plane.py",
    "engines.identity.routes_ticket": "engines/identity/routes_ticket.py",
    "engines.strategy_lock.routes": "engines/strategy_lock/routes.py",
    "engines.temperature.routes": "engines/temperature/routes.py",
    "engines.nexus.vector_explorer.routes": "engines/nexus/vector_explorer/routes.py",
    "engines.nexus.vector_ingest.routes": "engines/nexus/vector_explorer/ingest_routes.py",
    "engines.video_timeline.routes": "engines/muscle/video_timeline/routes.py",
    "engines.video_render.routes": "engines/muscle/video_render/routes.py",
    "engines.video_360.routes": "engines/muscle/video_360/routes.py",
    "engines.video_regions.routes": "engines/muscle/video_regions/routes.py",
    "engines.audio_service.routes": "engines/muscle/audio_service/routes.py",
    "engines.video_mask.routes": "engines/muscle/video_mask/routes.py",
    "engines.video_multicam.routes": "engines/muscle/video_multicam/routes.py",
    "engines.video_visual_meta.routes": "engines/muscle/video_visual_meta/routes.py",
    "engines.audio_semantic_timeline.routes": "engines/muscle/audio_semantic_timeline/routes.py",
    "engines.audio_voice_enhance.routes": "engines/muscle/audio_voice_enhance/routes.py",
    "engines.video_presets.routes": "engines/muscle/video_presets/routes.py",
    "engines.video_text.routes": "engines/muscle/video_text/routes.py",
    "engines.budget.routes": "engines/budget/routes.py",
    "engines.billing.routes": "engines/billing/routes.py",
    "engines.kpi.routes": "engines/kpi/routes.py",
    "engines.seo.routes": "engines/seo/routes.py",
    "engines.bossman.routes": "engines/bossman/routes.py",
    "engines.debug.aws_routes": "engines/debug/aws_routes.py",
    "engines.kill_switch.routes": "engines/kill_switch/routes.py",
    "engines.ops.status": "engines/ops/status.py",
    "engines.knowledge.routes": "engines/knowledge/routes.py",
    "engines.analytics_events.routes": "engines/analytics_events/routes.py",
    "engines.three_wise.routes": "engines/three_wise/routes.py",
    "engines.firearms.routes": "engines/firearms/routes.py",
    "engines.memory.routes": "engines/memory/routes.py",
    "engines.actions.router": "engines/actions/router.py",
    "engines.nexus.raw_storage.routes": "engines/nexus/raw_storage/routes.py",
    "engines.nexus.atoms.routes": "engines/nexus/atoms/routes.py",
    "engines.nexus.cards.routes": "engines/nexus/cards/routes.py",
    "engines.nexus.index.routes": "engines/nexus/index/routes.py",
    "engines.nexus.packs.routes": "engines/nexus/packs/routes.py",
    "engines.nexus.settings.routes": "engines/nexus/settings/routes.py",
    "engines.nexus.runs.routes": "engines/nexus/runs/routes.py",
    "engines.nexus.memory.routes": "engines/nexus/memory/routes.py",
    "engines.canvas_commands": "engines/canvas_commands/router.py",
    "engines.origin_snippets.routes": "engines/origin_snippets/routes.py",
    "engines.persistence.routes": "engines/persistence/routes.py",
    "engines.routing.routes": "engines/routing/routes.py",
    "engines.canvas_stream.router": "engines/canvas_stream/router.py",
    "engines.feature_flags.routes": "engines/feature_flags/routes.py",
    "engines.config_store.routes": "engines/config_store/routes.py",
    "engines.registry.routes": "engines/registry/routes.py",
}

print("Router Group\tIdentity Enforced\tError Envelope\tGateChain\tExists")

for name, rel_path in ROUTERS.items():
    abs_path = os.path.join(os.getcwd(), rel_path)
    if not os.path.exists(abs_path):
        print(f"{name}\t?\t?\t?\tFAIL_NOT_FOUND")
        continue

    with open(abs_path, 'r') as f:
        content = f.read()

    identity = "PASS" if "Depends(get_request_context)" in content else "FAIL"
    envelope = "PASS" if "ErrorEnvelope" in content else "FAIL"
    gatechain = "PASS" if "GateChain" in content or "get_gate_chain" in content else "FAIL"

    # Refine checks
    if "Depends(get_request_context)" not in content and "get_request_context" in content:
        # Might be imported but not used directly in Depends, or aliased.
        pass

    print(f"{name}\t{identity}\t{envelope}\t{gatechain}\tPASS")
