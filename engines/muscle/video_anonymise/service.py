from __future__ import annotations

import os
import uuid
from typing import Optional, List

from engines.common.identity import RequestContext
from engines.video_timeline.service import get_timeline_service, TimelineService
from engines.video_regions.service import get_video_regions_service, VideoRegionsService
from engines.video_regions.models import AnalyzeRegionsRequest
from engines.video_timeline.models import Filter, FilterStack
from engines.video_anonymise.models import AnonymiseFacesRequest, AnonymiseFacesResult

DEFAULT_FILTER_STRENGTH = float(os.getenv("VIDEO_ANONYMISE_DEFAULT_STRENGTH", "1.0"))


class VideoAnonymiseService:
    def __init__(
        self,
        timeline_service: Optional[TimelineService] = None,
        regions_service: Optional[VideoRegionsService] = None
    ):
        self.timeline_service = timeline_service or get_timeline_service()
        self.regions_service = regions_service or get_video_regions_service()

    def anonymise_sequence(
        self, req: AnonymiseFacesRequest, context: Optional[RequestContext] = None
    ) -> AnonymiseFacesResult:
        self._validate_tenant_env(req, context)
        # 1. Get Sequence Info
        # We need clips to find assets.
        # Assuming sequence exists.
        seqs = self.timeline_service.list_sequences_for_project(req.sequence_id) # API might work by ID or project?
        # Timeline service list_sequences typically takes project_id.
        # But we only have sequence_id.
        # We might need to list clips directly via sequence if supported.
        # Or fetch sequence by ID.
        # `list_tracks_for_sequence` requires sequence_id.
        
        tracks = self.timeline_service.list_tracks_for_sequence(req.sequence_id)
        if not tracks:
             # Maybe invalid sequence or empty
             return AnonymiseFacesResult(
                 sequence_id=req.sequence_id,
                 clips_modified_count=0,
                 clip_ids=[]
             )
             
        clips = []
        for t in tracks:
            # Only video tracks typically? The filter only applies to video.
            if t.kind == "video":
                clips.extend(self.timeline_service.list_clips_for_track(t.id))
        
        modified_clips = []
        
        for clip in clips:
            # 2. Analyze Asset
            # Idempotent call to regions
            reg_req = AnalyzeRegionsRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                user_id=req.user_id,
                asset_id=clip.asset_id,
                include_regions=["face"]
            )
            # This triggers analysis (and artifact registration)
            res = self.regions_service.analyze_regions(reg_req, context)
            
            # Check if faces detected.
            # We need to read the summary to know if we should add the filter?
            # Or just add the filter and let render engine be smart (if no masks, no blur)?
            # Render engine `resolve_region_masks_for_clip` returns empty map if no masks.
            # However, adding a filter that does nothing is wasteful but safe.
            # OPTIMIZATION: Check summary.
            summary = self.regions_service.get_analysis(res.summary_artifact_id)
            has_faces = False
            if summary:
                # Check for "face" entries
                has_faces = any(e.region == "face" for e in summary.entries)
            
            if has_faces:
                strength = req.filter_strength if req.filter_strength is not None else DEFAULT_FILTER_STRENGTH
                backend_version = summary.meta.get("backend_version")
                self._add_face_blur_filter(clip.id, req, strength, backend_version, res.summary_artifact_id)
                modified_clips.append(clip.id)
                
        return AnonymiseFacesResult(
            sequence_id=req.sequence_id,
            clips_modified_count=len(modified_clips),
            clip_ids=modified_clips
        )

    def _validate_tenant_env(
        self, req: AnonymiseFacesRequest, context: Optional[RequestContext]
    ) -> None:
        if not req.tenant_id or req.tenant_id == "t_unknown":
            raise ValueError("valid tenant_id is required")
        if not req.env:
            raise ValueError("env is required")
        if context and (context.tenant_id != req.tenant_id or context.env != req.env):
            raise ValueError("tenant/env mismatch with request context")

    def _add_face_blur_filter(
        self, clip_id: str, req: AnonymiseFacesRequest, strength: float, backend_version: Optional[str], summary_id: str
    ):
        # 3. Add Filter
        # Check existing stack
        stack = self.timeline_service.get_filter_stack_for_target("clip", clip_id)
        
        # Check if already has face_blur?
        # To avoid duplicates.
        if stack and stack.filters:
            if any(f.type == "face_blur" for f in stack.filters):
                return # Already present

        # Create new filter
        new_filter = Filter(
            type="face_blur",
            params={"strength": strength, "source_summary_id": summary_id},
            enabled=True
        )
        if backend_version:
            new_filter.params["backend_version"] = backend_version
        
        # Add to stack via service
        if not stack:
            stack = FilterStack(
                tenant_id=req.tenant_id,
                env=req.env,
                target_type="clip",
                target_id=clip_id,
                filters=[new_filter]
            )
            self.timeline_service.create_filter_stack(stack)
        else:
            stack.filters.append(new_filter)
            self.timeline_service.update_filter_stack(stack)


_default_service: Optional[VideoAnonymiseService] = None

def get_video_anonymise_service() -> VideoAnonymiseService:
    global _default_service
    if _default_service is None:
        _default_service = VideoAnonymiseService()
    return _default_service
