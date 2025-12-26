from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol

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
from engines.video_multicam.backend import MultiCamAlignBackend, LibrosaAlignBackend, StubAlignBackend
from engines.storage.gcs_client import GcsClient
import tempfile
import os
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

TIMECODE_ENV = "VIDEO_MULTICAM_TIMECODE_OFFSETS"
PACER_ENV = "VIDEO_MULTICAM_PACING_PRESET"
SAMPLE_RATE_HZ = 1000
ALIGNMENT_CACHE_VERSION = "v1"
PACING_PRESETS = {
    "fast": {"min": 1000, "max": 4000},
    "medium": {"min": 2000, "max": 6000},
    "slow": {"min": 3000, "max": 9000},
}
SCORE_VERSION = "v1"

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
        self.align_backend = align_backend or LibrosaAlignBackend()
        try:
            self.gcs = GcsClient()
        except Exception:
            self.gcs = None

    def _ensure_local(self, uri: str) -> str:
        if uri.startswith("gs://") and self.gcs:
            try:
                bucket_path = uri.replace("gs://", "", 1)
                bucket_name, key = bucket_path.split("/", 1)
                tmp_path = Path(tempfile.gettempdir()) / f"dl_align_{uuid.uuid4().hex}_{Path(key).name}"
                bucket = self.gcs._client.bucket(bucket_name) # type: ignore
                blob = bucket.blob(key)
                blob.download_to_filename(str(tmp_path))
                return str(tmp_path)
            except Exception:
                return uri
        return uri

    def _parse_timecode_overrides(self) -> Dict[str, int]:
        raw = os.getenv(TIMECODE_ENV)
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
            overrides: Dict[str, int] = {}
            for aid, value in payload.items():
                overrides[aid] = int(value)
            return overrides
        except Exception:
            logger.warning("Invalid timecode overrides in %s", TIMECODE_ENV)
            return {}

    def _waveform_samples_for_asset(self, asset) -> Optional[List[float]]:
        meta = getattr(asset, "meta", None) or {}
        raw = meta.get("waveform")
        if isinstance(raw, list) and raw:
            try:
                return [float(v) for v in raw]
            except Exception:
                return None
        return None

    def _cross_correlation_offset(self, master: List[float], angle: List[float], max_search_ms: int) -> int:
        if not master or not angle:
            return 0
        latency = min(max_search_ms, len(master), len(angle))
        best_corr = float("-inf")
        best_lag = 0
        lag_limit = int(latency)
        for lag in range(-lag_limit, lag_limit + 1):
            score = 0.0
            count = 0
            for idx, m_val in enumerate(master):
                ai = idx + lag
                if ai < 0 or ai >= len(angle):
                    continue
                score += m_val * angle[ai]
                count += 1
            if count == 0:
                continue
            corr = score / count
            if corr > best_corr or (corr == best_corr and abs(lag) < abs(best_lag)):
                best_corr = corr
                best_lag = lag
        return int(best_lag)

    def _align_via_backend(self, base_path: str, angle_path: str) -> float:
        try:
            return self.align_backend.calculate_offset(base_path, angle_path)
        except Exception as exc:
            logger.warning("Alignment backend failed: %s", exc)
            return 0.0

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
        
        # Enforce Tenant/Env
        if session.tenant_id != req.tenant_id:
             logger.warning("Tenant mismatch for session %s: req %s vs session %s", session.id, req.tenant_id, session.tenant_id)
             raise ValueError("Access Denied: Tenant mismatch")
        if session.env != req.env:
             logger.warning("Env mismatch for session %s: req %s vs session %s", session.id, req.env, session.env)
             raise ValueError("Access Denied: Environment mismatch")

        # Resolve paths
        asset_map = {}
        for t in session.tracks:
            asset = self.media_service.get_asset(t.asset_id)
            if asset:
                 local_path = self._ensure_local(asset.source_uri)
                 if os.path.exists(local_path):
                     asset_map[t.asset_id] = local_path
                 else:
                     asset_map[t.asset_id] = asset.source_uri

        base_asset_id = session.base_asset_id or session.tracks[0].asset_id
        base_path = asset_map.get(base_asset_id)
        if not base_path:
            raise ValueError(f"Base asset {base_asset_id} not resolvable")

        overrides = self._parse_timecode_overrides()
        cache_key = f"{req.alignment_method}:{req.max_search_ms}:{ALIGNMENT_CACHE_VERSION}"
        cached = session.meta.get("alignment_cache", {}).get(cache_key)
        
        offsets: Dict[str, int] = {}
        confidences: Dict[str, float] = {}
        cache_hit = False

        if cached:
            # V04 Upgrade: Support {"offsets": ..., "confidences": ...} or legacy dict[str, int]
            cache_hit = True
            if "offsets" in cached and isinstance(cached["offsets"], dict):
                offsets = dict(cached["offsets"])
                confidences = dict(cached.get("confidences", {}))
            else:
                # Legacy cache (just offsets)
                offsets = dict(cached)
                confidences = {} 
            
            logger.info("Alignment cache hit for session %s", session.id)
            
            if overrides:
                for aid, value in overrides.items():
                    if aid in offsets:
                        offsets[aid] = value
                        # If we override, confidence is manually enforced to 1.0? 
                        # Or we leave it as computed? 
                        # Let's say confidence is 1.0 for manual overrides.
                        confidences[aid] = 1.0
                        logger.info("Applied timecode override for %s -> %s ms", aid, value)
        else:
            mas = self.media_service.get_asset(base_asset_id)
            master_samples = self._waveform_samples_for_asset(mas) if mas else None
            
            for asset_id, path in asset_map.items():
                if asset_id == base_asset_id:
                    offsets[asset_id] = 0
                    confidences[asset_id] = 1.0
                    continue
                if req.alignment_method == "stub":
                    offsets[asset_id] = 0
                    confidences[asset_id] = 1.0
                    continue
                if req.alignment_method == "waveform_cross_correlation" and master_samples:
                    # Synthetic/Meta-based fallback
                    angle_asset = self.media_service.get_asset(asset_id)
                    angle_samples = self._waveform_samples_for_asset(angle_asset) or []
                    if angle_samples:
                        offsets[asset_id] = self._cross_correlation_offset(master_samples, angle_samples, req.max_search_ms)
                        confidences[asset_id] = 0.5 
                        logger.info("Cross-corr offset %s -> %s ms", asset_id, offsets[asset_id])
                        continue
                
                # Real Backend
                off, conf = self._align_via_backend(base_path, path)
                offsets[asset_id] = int(off)
                confidences[asset_id] = conf

            # Store structured cache
            session.meta.setdefault("alignment_cache", {})[cache_key] = {
                "offsets": offsets,
                "confidences": confidences
            }
            session.meta["last_alignment"] = {
                "method": req.alignment_method,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "offsets": offsets,
                "confidences": confidences,
            }

        # Update session
        for t in session.tracks:
            if t.asset_id in offsets:
                t.offset_ms = offsets[t.asset_id]
        
        self.repo.update(session)
        
        result_meta = {
            "method": req.alignment_method,
            "cache_key": cache_key,
            "cache_hit": cache_hit,
            "alignment_version": ALIGNMENT_CACHE_VERSION,
        }
        if confidences:
             result_meta["confidences"] = confidences

        if overrides:
            result_meta["timecode_overrides"] = overrides
        return MultiCamAlignResult(
            session_id=session.id,
            offsets_ms=offsets,
            meta=result_meta,
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

        assets_info: Dict[str, Dict[str, Any]] = {}
        total_duration = 0
        for t in session.tracks:
            asset = self.media_service.get_asset(t.asset_id)
            duration = asset.duration_ms if asset and asset.duration_ms else 60000
            offset = t.offset_ms or 0
            artifacts = self.media_service.list_artifacts_for_asset(t.asset_id)
            role = t.role or "primary"
            total_duration = max(total_duration, offset + duration)
            assets_info[t.asset_id] = {
                "asset_id": t.asset_id,
                "dur": duration,
                "offset": offset,
                "role": role,
                "artifacts": artifacts,
            }

        pacing_setting = os.getenv(PACER_ENV, "medium")
        pacing_conf = PACING_PRESETS.get(pacing_setting, PACING_PRESETS["medium"])
        min_shot = max(req.min_shot_duration_ms, pacing_conf["min"])
        max_shot = min(req.max_shot_duration_ms, pacing_conf["max"])
        if max_shot < min_shot:
            max_shot = min_shot

        if not assets_info:
            return MultiCamAutoCutResult(
                session_id=session.id,
                project_id=project_id,
                sequence_id=prog_seq.id,
                meta={"pacing_preset": pacing_setting, "score_version": SCORE_VERSION},
            )

        primary_assets = [aid for aid, info in assets_info.items() if info["role"] == "primary"]
        other_assets = [aid for aid in assets_info if aid not in primary_assets]
        all_assets = primary_assets + other_assets

        cursor = 0
        last_asset_id: Optional[str] = None
        score_cache: Dict[tuple[str, int], float] = {}

        while cursor < total_duration and all_assets:
            window_end = cursor + max_shot
            candidates: List[tuple[float, str]] = []
            energy_total = 0.0

            for aid in all_assets:
                info = assets_info.get(aid)
                if not info:
                    continue
                score = self._score_window(aid, cursor, window_end, info, last_asset_id, score_cache)
                if score <= 0:
                    continue
                candidates.append((score, aid))
                energy_total += score

            if not candidates:
                cursor += max_shot
                continue

            avg_energy = energy_total / len(candidates)
            candidates.sort(key=lambda x: x[0], reverse=True)
            chosen_id = candidates[0][1]

            duration_span = max_shot - min_shot
            if duration_span <= 0:
                base_duration = min_shot
            else:
                energy_factor = min(1.0, avg_energy)
                base_duration = min_shot + (1.0 - energy_factor) * duration_span
            pace_mult = {"fast": 0.9, "medium": 1.0, "slow": 1.1}.get(pacing_setting, 1.0)
            shot_dur = max(min_shot, min(max_shot, int(base_duration * pace_mult)))

            info = assets_info[chosen_id]
            offset = info["offset"]
            asset_start = cursor - offset
            asset_end = asset_start + shot_dur
            start_clamped = max(0, asset_start)
            end_clamped = min(info["dur"], asset_end)
            actual_duration = int(max(1, end_clamped - start_clamped))
            if actual_duration <= 0:
                cursor += min_shot
                continue

            clip = Clip(
                track_id=prog_track.id,
                tenant_id=req.tenant_id,
                env=req.env,
                user_id=req.user_id,
                asset_id=chosen_id,
                start_ms_on_timeline=int(cursor),
                in_ms=int(start_clamped),
                out_ms=int(start_clamped + actual_duration)
            )
            self.timeline_service.create_clip(clip)
            last_asset_id = chosen_id
            cursor += max(actual_duration, min_shot)

        session.meta.setdefault("autocut_history", []).append(
            {
                "preset": pacing_setting,
                "score_version": SCORE_VERSION,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return MultiCamAutoCutResult(
            session_id=session.id,
            project_id=project_id,
            sequence_id=prog_seq.id,
            meta={"pacing_preset": pacing_setting, "score_version": SCORE_VERSION},
        )

    def _score_window(
        self,
        asset_id: str,
        start: float,
        end: float,
        info: Dict[str, Any],
        last_asset_id: Optional[str],
        cache: Dict[tuple[str, int], float],
    ) -> float:
        key = (asset_id, int(start))
        if key in cache:
            return cache[key]
        sem = self._semantic_energy(info, start, end)
        vis = self._visual_motion_score(info, start, end)
        score = 0.6 * sem + 0.4 * vis
        if info.get("role") == "primary":
            score += 0.15
        if asset_id == last_asset_id:
            score += 0.1
        score = min(1.0, score)
        if score <= 0:
            logger.info("Auto-cut falling back to stub score for %s at %s", asset_id, start)
        cache[key] = score
        return score

    def _semantic_energy(self, info: Dict[str, Any], start: float, end: float) -> float:
        # artifacts is list of Artifact objects. We need to check 'kind' and 'meta'.
        # `info['artifacts']` came from media_service.list_artifacts_for_asset.
        # Assuming they are dicts or objects. `list_artifacts_for_asset` returns objects usually.
        # Code above accessed `art.kind`.
        window_len = max(1.0, end - start)
        coverage = 0.0
        found = False
        
        for art in info.get("artifacts", []):
            # Check kind. Handle both "audio_semantic_timeline" and potential future types
            if getattr(art, "kind", "") != "audio_semantic_timeline":
                continue
            
            # Semantic events are in art.meta["events"]
            meta = getattr(art, "meta", {}) or {}
            events = meta.get("events", [])
            for evt in events:
                # We care about "speech" or maybe "music" if it's a music video?
                # For multicam dialogue, "speech" is king.
                if evt.get("kind") != "speech":
                    continue
                    
                evt_start = evt.get("start_ms")
                evt_end = evt.get("end_ms")
                if evt_start is None or evt_end is None:
                    continue
                
                # Intersection
                overlap_start = max(start, evt_start)
                overlap_end = min(end, evt_end)
                overlap = max(0.0, overlap_end - overlap_start)
                
                if overlap > 0:
                    found = True
                    coverage += overlap
        
        if not found:
             # Fallback: if no semantic timeline exists, return 0 (neutral) or maybe small value?
             # But if it exists and has no speech, return 0.
             # If NO artifact exists, we might want to return 0.5 (neutral) so we don't punish it?
             # Logic above: "found = True" only if we see overlap.
             # If artifact missing, loop finishes found=False.
             # Log debug.
             return 0.0
             
        # Normalize
        ratio = coverage / window_len
        # Boost ratio so even 50% speech feels "active"
        score = min(1.0, ratio * 1.5)
        return score

    def _visual_motion_score(self, info: Dict[str, Any], start: float, end: float) -> float:
        samples: List[float] = []
        found_artifact = False
        
        for art in info.get("artifacts", []):
            kind = getattr(art, "kind", "")
            if kind not in ("visual_meta", "video_visual_meta"):
                continue
            
            found_artifact = True
            meta = getattr(art, "meta", {}) or {}
            frames = meta.get("frames", [])
            
            # Simple frame sampling
            for frame in frames:
                ts = frame.get("timestamp_ms")
                if ts is None:
                    continue
                if start <= ts < end:
                    # Prefer "motion_score", fallback to "primary_subject_movement"
                    val = frame.get("motion_score")
                    if val is None:
                         val = frame.get("primary_subject_movement", 0.0)
                    samples.append(float(val))
        
        if not found_artifact:
             # If no visual meta, assume moderate motion to avoid penalizing
             return 0.2
             
        if not samples:
            return 0.0
            
        avg = sum(samples) / len(samples)
        return min(1.0, avg)

_default_service: Optional[MultiCamService] = None

def get_multicam_service() -> MultiCamService:
    global _default_service
    if _default_service is None:
        _default_service = MultiCamService()
    return _default_service
