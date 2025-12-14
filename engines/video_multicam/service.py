from __future__ import annotations

import random
from typing import Dict, List, Optional, Protocol

from engines.media_v2.service import MediaService, get_media_service
from engines.video_multicam.models import (
    CreateMultiCamSessionRequest,
    MultiCamAlignRequest,
    MultiCamAlignResult,
    MultiCamAutoCutRequest,
    MultiCamAutoCutResult,
    MultiCamBuildSequenceRequest,
    MultiCamBuildSequenceResult,
    MultiCamSession,
    MultiCamTrackSpec,
)
from engines.video_timeline.models import Clip, Sequence, Track, VideoProject
from engines.video_timeline.service import TimelineService, get_timeline_service
from engines.align.service import AlignService, get_align_service

class MultiCamAlignBackend(Protocol):
    def calculate_offset(self, master_audio_path: str, angle_audio_path: str) -> float:
        ...

class StubAlignBackend:
    def calculate_offset(self, master_audio_path: str, angle_audio_path: str) -> float:
        return 0.0

class InMemorySessionRepository:
    def __init__(self):
        self.sessions: Dict[str, MultiCamSession] = {}

    def create(self, session: MultiCamSession) -> MultiCamSession:
        self.sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Optional[MultiCamSession]:
        return self.sessions.get(session_id)

    def list(self, tenant_id: str) -> List[MultiCamSession]:
        return [s for s in self.sessions.values() if s.tenant_id == tenant_id]

    def update(self, session: MultiCamSession) -> MultiCamSession:
        self.sessions[session.id] = session
        return session


class MultiCamService:
    def __init__(
        self,
        media_service: Optional[MediaService] = None,
        timeline_service: Optional[TimelineService] = None,
        align_backend: Optional[MultiCamAlignBackend] = None,
    ):
        self.repo = InMemorySessionRepository()
        self.media_service = media_service or get_media_service()
        self.timeline_service = timeline_service or get_timeline_service()
        self.repo = InMemorySessionRepository()
        self.media_service = media_service or get_media_service()
        self.timeline_service = timeline_service or get_timeline_service()
        self.align_service = align_backend or get_align_service()

    def create_session(self, req: CreateMultiCamSessionRequest) -> MultiCamSession:
        # Validate assets exist
        for track in req.tracks:
            asset = self.media_service.get_asset(track.asset_id)
            if not asset:
                raise ValueError(f"Asset not found: {track.asset_id}")
            if asset.kind != "video":
                raise ValueError(f"Asset {track.asset_id} is not a video")

        session = MultiCamSession(
            tenant_id=req.tenant_id,
            env=req.env,
            user_id=req.user_id,
            project_id=req.project_id,
            name=req.name,
            tracks=req.tracks,
            base_asset_id=req.base_asset_id or req.tracks[0].asset_id,
        )
        return self.repo.create(session)

    def get_session(self, session_id: str) -> Optional[MultiCamSession]:
        return self.repo.get(session_id)

    def list_sessions(self, tenant_id: str, project_id: Optional[str] = None) -> List[MultiCamSession]:
        sessions = self.repo.list(tenant_id)
        if project_id:
            sessions = [s for s in sessions if s.project_id == project_id]
        return sessions

    def align_session(self, req: MultiCamAlignRequest) -> MultiCamAlignResult:
        session = self.get_session(req.session_id)
        if not session:
            raise ValueError("Session not found")

        # Resolve local paths (mocked here by URI for stub backend)
        # In real impl, use media_service to download/resolve
        # Prepare local paths
        # Logic to ensure local file path omitted for V1 stub simplicity
        # We pass source_uri which the backend might use or ignore
        asset_map = {}
        for t in session.tracks:
            asset = self.media_service.get_asset(t.asset_id)
            if asset:
                 asset_map[t.asset_id] = asset.source_uri

        base_asset_id = session.base_asset_id or session.tracks[0].asset_id
        base_path = asset_map.get(base_asset_id)
        if not base_path:
            raise ValueError(f"Base asset {base_asset_id} not resolvable")

        offsets = {}
        for asset_id, path in asset_map.items():
            if asset_id == base_asset_id:
                offsets[asset_id] = 0
                continue
            
            # Backend returns offset relative to master
            # Positive offset means angle audio should be delayed (started later) to match master
            # MultiCamTrackSpec.offset_ms matches this semantics
            try:
                # AlignService: align_service.calculate_offset(master, angle)
                # Note: our Protocol definition above might mismatch AlignService if we aren't careful.
                # AlignService has `calculate_offset`.
                # We cast align_service to Any or ensure Protocol matches.
                # Actually, AlignService is concrete.
                offset = self.align_service.calculate_offset(base_path, path)
                offsets[asset_id] = int(offset)
            except Exception:
                offsets[asset_id] = 0

        # Update session
        for t in session.tracks:
            if t.asset_id in offsets:
                t.offset_ms = offsets[t.asset_id]
        
        self.repo.update(session)
        
        return MultiCamAlignResult(
            session_id=session.id,
            offsets_ms=offsets
        )

    def build_sequence(self, req: MultiCamBuildSequenceRequest) -> MultiCamBuildSequenceResult:
        session = self.get_session(req.session_id)
        if not session:
            raise ValueError("Session not found")

        # 1. Ensure Project
        project_id = req.project_id or session.project_id
        if not project_id:
            project = self.timeline_service.create_project(
                VideoProject(
                    tenant_id=req.tenant_id,
                    env=req.env,
                    user_id=req.user_id,
                    title=f"{session.name} Project"
                )
            )
            project_id = project.id
            # Update session link
            session.project_id = project_id
            self.repo.update(session)

        # 2. Create Sequence
        sequence = self.timeline_service.create_sequence(
            Sequence(
                project_id=project_id,
                tenant_id=req.tenant_id,
                env=req.env,
                user_id=req.user_id,
                name=f"{session.name} - Multicam Raw"
            )
        )

        track_map = {}
        
        # 3. Create Tracks & Clips
        # Sort tracks to ensure consistent order (e.g. primary top or bottom)
        # Usually primary is Track 1 (bottom) or we stack them. 
        # Let's stack them: Track 1 = Cam 1, Track 2 = Cam 2
        for idx, cam_track in enumerate(session.tracks):
             # Create Timeline Track
             video_track = self.timeline_service.create_track(
                 Track(
                     sequence_id=sequence.id,
                     tenant_id=req.tenant_id,
                     env=req.env,
                     kind="video",
                     order=idx,
                     meta={"multicam_role": cam_track.role, "label": cam_track.label}
                 )
             )
             
             # Create Clip
             # Offset handles shifts. If offset > 0, clip starts at offset.
             # If offset < 0, we cut into the clip (in_ms = -offset) and start at 0? 
             # Or just place at start_ms_on_timeline = offset (if timeline supports negative start? No)
             # V1 assumption: timeline starts at 0.
             # We shift everyone so the earliest starts at 0.
             
             offset = cam_track.offset_ms or 0
             start_ms = max(0, offset)
             in_ms = max(0, -offset)

             asset = self.media_service.get_asset(cam_track.asset_id)
             duration = asset.duration_ms if asset and asset.duration_ms else 60000 # fallback
             
             clip = self.timeline_service.create_clip(
                 Clip(
                     track_id=video_track.id,
                     tenant_id=req.tenant_id,
                     env=req.env,
                     asset_id=cam_track.asset_id,
                     start_ms_on_timeline=start_ms,
                     in_ms=in_ms,
                     out_ms=in_ms + duration
                 )
             )
             track_map[cam_track.asset_id] = video_track.id

        return MultiCamBuildSequenceResult(
            session_id=session.id,
            project_id=project_id,
            sequence_id=sequence.id,
            track_ids=track_map
        )
    
    def auto_cut_sequence(self, req: MultiCamAutoCutRequest) -> MultiCamAutoCutResult:
        session = self.get_session(req.session_id)
        if not session:
             raise ValueError("Session not found")

        project_id = req.project_id or session.project_id or "unknown"
        
        # Create Program Sequence
        prog_seq = self.timeline_service.create_sequence(
            Sequence(
                project_id=project_id,
                tenant_id=req.tenant_id,
                env=req.env,
                user_id=req.user_id,
                name=f"{session.name} - Program Cut"
            )
        )
        
        prog_track = self.timeline_service.create_track(
            Track(
                sequence_id=prog_seq.id,
                tenant_id=req.tenant_id,
                env=req.env,
                kind="video",
                order=0,
                meta={"role": "program"}
            )
        )

        # Logic: Iterate time
        # Find min offsets to determine common start? Assumed 0 for now.
        # Determine total duration (max end of any track)
        total_duration = 0
        assets_info = {}
        for t in session.tracks:
             asset = self.media_service.get_asset(t.asset_id)
             dur = asset.duration_ms if asset else 0
             offset = t.offset_ms or 0
             total_duration = max(total_duration, offset + dur)
             assets_info[t.asset_id] = {"dur": dur, "offset": offset, "role": t.role}

        cursor = 0
        rng = random.Random(session.id) # Deterministic seed

        primary_assets = [t.asset_id for t in session.tracks if t.role == "primary"]
        other_assets = [t.asset_id for t in session.tracks if t.role != "primary"]
        
        if not primary_assets and other_assets:
            primary_assets = [other_assets[0]] # fallback
        
        all_assets = primary_assets + other_assets

        while cursor < total_duration:
            # Pick Duration
            shot_dur = rng.randint(req.min_shot_duration_ms, req.max_shot_duration_ms)
            if cursor + shot_dur > total_duration:
                shot_dur = total_duration - cursor
            
            # Pick Camera
            if rng.random() < req.prefer_primary_ratio and primary_assets:
                candidates = primary_assets
            else:
                candidates = other_assets if other_assets else primary_assets
            
            chosen_id = rng.choice(candidates) if candidates else (all_assets[0] if all_assets else None)

            if chosen_id:
                info = assets_info.get(chosen_id, {"offset": 0})
                offset = info["offset"]
                
                # Clip logic
                # Timeline start: cursor
                # Asset (Clip) time: cursor - offset (if offset is shift right)
                # Ensure we are inside asset bounds
                asset_time_start = cursor - offset
                
                # Check valid bounds
                # If asset_time_start < 0, this cam hasn't started yet.
                # If asset_time_start > dur, this cam ended.
                # Handling holes: For now, just place it. Timeline service handles bounds usually?
                # We'll just set in_ms/out_ms.
                
                in_ms = max(0, asset_time_start) # can't be negative
                # Adjust timeline placement if we clipped head
                tl_start = cursor + (in_ms - asset_time_start) 

                self.timeline_service.create_clip(
                    Clip(
                        track_id=prog_track.id,
                        tenant_id=req.tenant_id,
                        env=req.env,
                        asset_id=chosen_id,
                        start_ms_on_timeline=int(tl_start),
                        in_ms=int(in_ms),
                        out_ms=int(in_ms + shot_dur)
                    )
                )

            cursor += shot_dur

        return MultiCamAutoCutResult(
            session_id=session.id,
            project_id=project_id,
            sequence_id=prog_seq.id
        )

_default_service: Optional[MultiCamService] = None

def get_multicam_service() -> MultiCamService:
    global _default_service
    if _default_service is None:
        _default_service = MultiCamService()
    return _default_service
