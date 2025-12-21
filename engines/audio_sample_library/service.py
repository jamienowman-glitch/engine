from __future__ import annotations

from typing import List, Optional

from engines.media_v2.models import DerivedArtifact
from engines.media_v2.service import MediaService, get_media_service
from engines.audio_sample_library.models import SampleLibraryQuery, SampleLibraryResult, SampleDescriptor


class AudioSampleLibraryService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()

    def query_samples(self, query: SampleLibraryQuery) -> SampleLibraryResult:
        # 1. Fetch Candidates from Media V2
        # integrated with media_v2.service.MediaService
        # We assume it supports list_artifacts(tenant_id, env) filtering at DB level would be better
        # but for V1 we list and filter in memory as per plan "Service hardening".
        
        try:
             # Try to pass parent_asset_id if present to reduce scan
             artifacts = self.media_service.list_artifacts(
                 tenant_id=query.tenant_id, 
                 env=query.env, 
                 parent_asset_id=query.parent_asset_id
             )
        except AttributeError:
             # Fallback: if list_artifacts not exposed, use empty list
             print("WARNING: media_service.list_artifacts not found.")
             artifacts = []

        # 2. Filter In-Memory
        descriptors = []
        
        # Normalize kinds
        target_kinds = query.kinds or ([query.kind] if query.kind else ["audio_hit", "audio_loop", "audio_phrase"])
        
        for art in artifacts:
            # Type Check
            if art.kind not in target_kinds:
                continue
            
            # Meta Filters
            meta = art.meta or {}
            
            # BPM
            if query.min_bpm is not None:
                bpm = meta.get("bpm")
                if bpm is None or float(bpm) < query.min_bpm:
                    continue
            
            if query.max_bpm is not None:
                bpm = meta.get("bpm")
                if bpm is None or float(bpm) > query.max_bpm:
                    continue
                    
            # Bars
            if query.loop_bars is not None:
                bars = meta.get("loop_bars")
                if bars != query.loop_bars:
                    continue
                    
            # Transcript
            if query.has_transcript:
                if not meta.get("transcript"):
                    continue

            # P2: Key Root
            # features might be inside 'features' dict or top level if older?
            # We assume features are under 'features' key in meta based on audio_normalise implementation.
            feats = meta.get("features", {})
            if query.key_root:
                # Allow partial match or exact? Exact for "C".
                # If key_root is "C", we want "C" exactly? 
                # What about "C#" vs "C"?
                k = feats.get("key_root")
                if k != query.key_root:
                     continue
            
            # Brightness
            if query.min_brightness is not None:
                b = feats.get("brightness")
                if b is None or float(b) < query.min_brightness:
                    continue
            
            if query.max_brightness is not None:
                b = feats.get("brightness")
                if b is None or float(b) > query.max_brightness:
                    continue

            if query.min_quality_score is not None:
                quality = meta.get("quality_score")
                if quality is None or float(quality) < query.min_quality_score:
                    continue

            if query.max_quality_score is not None:
                quality = meta.get("quality_score")
                if quality is None or float(quality) > query.max_quality_score:
                    continue

            if query.role:
                if meta.get("role") != query.role:
                    continue

            # Check passed
            descriptors.append(self._map_to_descriptor(art))
        
        # 3. Sort (Deterministic)
        # Sort by kind, then start_ms, then id
        descriptors.sort(key=lambda x: (x.kind, x.source_start_ms or 0, x.artifact_id))

        # 4. Pagination
        total = len(descriptors)
        start = query.offset
        end = start + query.limit
        sliced = descriptors[start:end]

        return SampleLibraryResult(
            samples=sliced,
            total_count=total,
            filter_summary=query.model_dump(exclude={"user_id"})
        )

    def _map_to_descriptor(self, art: DerivedArtifact) -> SampleDescriptor:
        meta = art.meta or {}
        feats = meta.get("features", {})
        
        return SampleDescriptor(
            artifact_id=art.id,
            asset_id=art.parent_asset_id,
            kind=art.kind, # type: ignore
            uri=art.uri,
            source_start_ms=art.start_ms,
            source_end_ms=art.end_ms,
            bpm=meta.get("bpm") or feats.get("bpm"),
            loop_bars=meta.get("loop_bars"),
            peak_db=meta.get("peak_db") or meta.get("norm_stats", {}).get("output_tp"),
            quality_score=meta.get("quality_score"),
            transcript=meta.get("transcript"),
            
            # P2 Fields
            key_root=feats.get("key_root"),
            brightness=feats.get("brightness"),
            noisiness=feats.get("noisiness"),
            features=feats,
            role=meta.get("role"),
            
            meta=meta
        )

_default_service: Optional[AudioSampleLibraryService] = None

def get_audio_sample_library_service() -> AudioSampleLibraryService:
    global _default_service
    if _default_service is None:
        _default_service = AudioSampleLibraryService()
    return _default_service
