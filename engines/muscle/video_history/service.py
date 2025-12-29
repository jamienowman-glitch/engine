import uuid
import json
from typing import Optional, List, Dict
from engines.video_history.models import Snapshot, Diff, Change
from engines.video_timeline.service import TimelineService, get_timeline_service

class HistoryService:
    def __init__(self, timeline_service: Optional[TimelineService] = None):
        self.timeline_service = timeline_service or get_timeline_service()
        self._snapshots: Dict[str, Snapshot] = {}

    def snapshot(self, sequence_id: str, description: Optional[str] = None) -> Optional[Snapshot]:
        seq = self.timeline_service.get_sequence(sequence_id)
        if not seq:
            return None
            
        tracks = self.timeline_service.list_tracks_for_sequence(sequence_id)
        # Deep serialization
        # Just capturing IDs for V1 diff logic
        track_ids = [t.id for t in tracks]
        clip_ids = []
        for t in tracks:
            clips = self.timeline_service.list_clips_for_track(t.id)
            clip_ids.extend([c.id for c in clips])
            
        data = {
            "sequence_id": sequence_id,
            "track_ids": sorted(track_ids),
            "clip_ids": sorted(clip_ids)
        }
        
        snap = Snapshot(
            id=uuid.uuid4().hex,
            sequence_id=sequence_id,
            data=data,
            description=description
        )
        self._snapshots[snap.id] = snap
        return snap

    def diff(self, snapshot_a_id: str, snapshot_b_id: str) -> Optional[Diff]:
        snap_a = self._snapshots.get(snapshot_a_id)
        snap_b = self._snapshots.get(snapshot_b_id)
        
        if not snap_a or not snap_b:
            return None
            
        changes = []
        
        # Compare Clips
        clips_a = set(snap_a.data.get("clip_ids", []))
        clips_b = set(snap_b.data.get("clip_ids", []))
        
        added = clips_b - clips_a
        removed = clips_a - clips_b
        
        for cid in added:
            changes.append(Change(type="ADD", target_type="CLIP", target_id=cid))
        for cid in removed:
            changes.append(Change(type="REMOVE", target_type="CLIP", target_id=cid))
            
        return Diff(
            snapshot_a_id=snapshot_a_id,
            snapshot_b_id=snapshot_b_id,
            changes=changes
        )

_svc = None
def get_history_service() -> HistoryService:
    global _svc
    if _svc is None:
        _svc = HistoryService()
    return _svc
