from typing import List, Optional
from engines.video_render.service import get_render_service, RenderService
from engines.video_timeline.service import get_timeline_service, TimelineService
from engines.video_preview.models import PreviewRequest, PreviewResult

class PreviewService:
    def __init__(self, 
                 render_service: Optional[RenderService] = None,
                 timeline_service: Optional[TimelineService] = None):
        self.render_service = render_service or get_render_service()
        self.timeline_service = timeline_service or get_timeline_service()

    def get_preview_stream(self, req: PreviewRequest) -> Optional[PreviewResult]:
        seq = self.timeline_service.get_sequence(req.sequence_id)
        if not seq:
            return None
        tracks = self.timeline_service.list_tracks_for_sequence(seq.id)
        clip_found = False
        for track in tracks:
            clips = self.timeline_service.list_clips_for_track(track.id)
            if clips:
                clip_found = True
                break
        preview_warnings: List[str] = []
        if not tracks:
            preview_warnings.append("no_tracks_for_preview")
        elif not clip_found:
            preview_warnings.append("no_clips_for_preview")
        try:
            self.render_service.ensure_proxies_for_project(seq.project_id)
        except Exception as exc:
            preview_warnings.append(f"proxy_generation_failed:{exc}")
        requested_profile = "draft_480p_fast" if req.strategy == "DRAFT" else "preview_720p_fast"
        backend_profile = requested_profile if requested_profile != "draft_480p_fast" else "preview_720p_fast"
        estimated_latency = 200 if requested_profile == "draft_480p_fast" else 500
        from engines.video_render.models import RenderRequest

        r_req = RenderRequest(
            tenant_id=seq.tenant_id,
            env=seq.env,
            user_id=seq.user_id,
            project_id=seq.project_id,
            render_profile=backend_profile,
            use_proxies=True,
            dry_run=True,
        )
        res = self.render_service.render(r_req)
        render_plan = res.plan_preview
        if requested_profile != backend_profile:
            render_plan.profile = requested_profile
            render_plan.meta.setdefault("preview_profile", backend_profile)
        if preview_warnings:
            render_plan.meta.setdefault("preview_warnings", []).extend(preview_warnings)
        return PreviewResult(
            sequence_id=req.sequence_id,
            render_plan=render_plan.model_dump(),
            estimated_latency_ms=estimated_latency,
        )

_svc = None
def get_preview_service() -> PreviewService:
    global _svc
    if _svc is None:
        _svc = PreviewService()
    return _svc
