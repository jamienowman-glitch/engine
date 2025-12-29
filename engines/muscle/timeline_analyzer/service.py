from typing import Optional, List, Tuple
from engines.video_timeline.service import get_timeline_service, TimelineService
from engines.timeline_analyzer.models import HealthReport, ComplexityMetric, HealthStatus

class TimelineAnalyzerService:
    def __init__(self, timeline_service: Optional[TimelineService] = None):
        self.timeline_service = timeline_service or get_timeline_service()

    def analyze(self, sequence_id: str) -> Optional[HealthReport]:
        seq = self.timeline_service.get_sequence(sequence_id)
        if not seq:
            return None
        
        tracks = self.timeline_service.list_tracks_for_sequence(sequence_id)
        all_clips = []
        for t in tracks:
            # Note: This is N+1, optimize later
            clips = self.timeline_service.list_clips_for_track(t.id)
            all_clips.extend(clips)
            
        # 1. Basic Counts
        metric_tracks = ComplexityMetric(name="Track Count", value=len(tracks), threshold=10)
        if len(tracks) > 10:
            metric_tracks.status = "WARNING"
            
        metric_clips = ComplexityMetric(name="Clip Count", value=len(all_clips), threshold=50)
        if len(all_clips) > 50:
            metric_clips.status = "WARNING" # Heuristic
            
        # 2. Total Duration (from seq metadata or max clip)
        max_end = 0.0
        for c in all_clips:
            # c.start_ms_on_timeline is float
            end = c.start_ms_on_timeline + (c.out_ms - c.in_ms)
            if end > max_end:
                max_end = end
                
        duration_sec = max_end / 1000.0
        metric_dur = ComplexityMetric(name="Duration (s)", value=duration_sec)
        
        # 3. Overlap Density (Max Concurrent Video Streams)
        # Only count 'video' tracks for rendering complexity, usually audio is cheap(ish)
        # But 'all_clips' includes audio if track is audio.
        # Let's count video density specificially?
        # For general complexity, let's just count all active clips.
        
        events: List[Tuple[float, int]] = []
        for c in all_clips:
            start = c.start_ms_on_timeline
            end = start + (c.out_ms - c.in_ms)
            events.append((start, 1))
            events.append((end, -1))
            
        events.sort(key=lambda x: (x[0], x[1])) # Sort by time, then type (-1 before +1? No, usually +1 before -1 if same time?)
        # Actually if same time: End one clip, Start another.
        # If we process End (-1) before Start (1), we avoid spike.
        # So sort key should prefer -1 for same time.
        # But here 1 > -1. So (t, -1) comes before (t, 1)? No, -1 < 1.
        # So (t, -1) comes FIRST. This is good. It means overlap drops before rising.
        
        max_overlap = 0
        current_overlap = 0
        for _, change in events:
            current_overlap += change
            if current_overlap > max_overlap:
                max_overlap = current_overlap
                
        metric_density = ComplexityMetric(name="Max Overlap", value=max_overlap, threshold=6)
        if max_overlap > 6:
            metric_density.status = "WARNING"
            
        # 4. Overall Status
        metrics = [metric_tracks, metric_clips, metric_dur, metric_density]
        overall = "OK"
        messages = []
        
        for m in metrics:
            if m.status == "CRITICAL":
                overall = "CRITICAL"
            elif m.status == "WARNING" and overall != "CRITICAL":
                overall = "WARNING"
                messages.append(f"{m.name} is high ({m.value} > {m.threshold})")
                
        if len(tracks) == 0:
            overall = "CRITICAL"
            messages.append("Sequence is empty (no tracks)")
            
        return HealthReport(
            sequence_id=sequence_id,
            overall_status=overall, # type: ignore
            metrics=metrics,
            messages=messages
        )

_svc = None
def get_analyzer_service() -> TimelineAnalyzerService:
    global _svc
    if _svc is None:
        _svc = TimelineAnalyzerService()
    return _svc
