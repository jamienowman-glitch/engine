import uuid
from typing import Optional, List
from engines.video_motifs.models import Motif, MotifClip
from engines.video_timeline.service import TimelineService, get_timeline_service
from engines.video_timeline.models import Clip

class MotifService:
    def __init__(self, timeline_service: Optional[TimelineService] = None):
        self.timeline_service = timeline_service or get_timeline_service()

    def extract_motif(self, sequence_id: str, start_ms: int, end_ms: int) -> Optional[Motif]:
        # Logic: Find clips in range, normalize time
        # Simplified V1: Just list clips
        tracks = self.timeline_service.list_tracks_for_sequence(sequence_id)
        if not tracks:
            return None
            
        motif_clips = []
        base_time = start_ms
        
        for idx, track in enumerate(tracks):
            clips = self.timeline_service.list_clips_for_track(track.id)
            for c in clips:
                c_start = c.start_ms_on_timeline
                c_end = c_start + (c.out_ms - c.in_ms)
                
                # Check overlap with range
                if c_end > start_ms and c_start < end_ms:
                    # Clip is inside or overlaps
                    # Calculate relative
                    rel_start = max(0, c_start - base_time)
                    duration = min(c_end, end_ms) - max(c_start, start_ms)
                    
                    mc = MotifClip(
                        relative_start_ms=rel_start,
                        duration_ms=duration,
                        track_offset=idx,
                        role="main" 
                    )
                    motif_clips.append(mc)
        
        if not motif_clips:
            return None
            
        return Motif(
            id=uuid.uuid4().hex,
            name="New Motif",
            clips=motif_clips
        )

    def apply_motif(self, target_sequence_id: str, motif: Motif, at_time_ms: int):
        # Stub logic for V1: Just print or return planned clips
        # Real logic: Create clips in target sequence
        pass

_svc = None
def get_motif_service() -> MotifService:
    global _svc
    if _svc is None:
        _svc = MotifService()
    return _svc
