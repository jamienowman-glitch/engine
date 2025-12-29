from __future__ import annotations
import json
import uuid
import tempfile
from pathlib import Path
from typing import Optional

from engines.media_v2.service import MediaService, get_media_service
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest, DerivedArtifact
from engines.audio_mix_snapshot.models import MixSnapshot, TrackState, CaptureRequest, DeltaRequest, MixDelta
from engines.audio_mix_snapshot.delta import compute_delta

class AudioMixSnapshotService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()

    def capture_snapshot(self, req: CaptureRequest) -> MixSnapshot:
        # Parse sequence dict to Snapshot
        # Input format mimics AudioSequence structure (tracks list)
        tracks_data = {}
        complexity = 0
        
        seq = req.audio_sequence
        raw_tracks = seq.get("tracks", [])
        
        for t in raw_tracks:
            # Assuming AudioTrack dict structure
            t_name = t.get("name", "unknown")
            # If name duplicate, suffix?
            if t_name in tracks_data:
                t_name = f"{t_name}_{uuid.uuid4().hex[:4]}"
            
            # Extract state
            # Assuming clips might have effects? Or track effects?
            # V1: just basics
            meta = t.get("meta", {})
            gain = meta.get("gain_db", 0.0) # Or t.get("gain_db") if added to model
            pan = meta.get("pan", 0.0)
            
            tracks_data[t_name] = TrackState(
                name=t_name,
                gain_db=gain,
                pan=pan,
                active=True, # Assuming active
                effects=[] # No track FX in V1 model yet
            )
            complexity += 1
            
        snap_id = uuid.uuid4().hex
        snapshot = MixSnapshot(
            id=snap_id,
            tracks=tracks_data,
            complexity_score=complexity,
            meta={"source": "capture"}
        )
        
        # Register Artifact
        payload = snapshot.model_dump_json(indent=2).encode('utf-8')
        fname = f"snapshot_{snap_id}.json"
        
        up_req = MediaUploadRequest(
             tenant_id=req.tenant_id, env=req.env, kind="other", # JSON
             source_uri="pending", tags=["generated", "snapshot"]
        )
        new_asset = self.media_service.register_upload(up_req, fname, payload)
        
        self.media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                parent_asset_id=new_asset.id,
                kind="audio_mix_snapshot", # Add to models
                uri=new_asset.source_uri,
                meta={"snapshot_id": snap_id}
            )
        )
        
        return snapshot

    def compare_snapshots(self, req: DeltaRequest) -> MixDelta:
        # 1. Get Artifacts
        art_a = self.media_service.get_artifact(req.snapshot_a_id)
        art_b = self.media_service.get_artifact(req.snapshot_b_id)
        
        if not art_a or not art_b:
             raise ValueError("Snapshot artifact not found")
             
        # 2. Load JSON
        # For V1, assuming local file read via Path (mocked in tests or local env)
        # In real storage, would download.
        
        try:
            # Helper to load
            snap_a = self._load_snapshot(art_a)
            snap_b = self._load_snapshot(art_b)
        except Exception:
            raise ValueError("Failed to load snapshot data")
            
        return compute_delta(snap_a, snap_b)

    def _load_snapshot(self, artifact: DerivedArtifact) -> MixSnapshot:
        # Read file
        p = Path(artifact.uri)
        if not p.exists():
            # In test environment, we might need to mock this read or ensure file exists.
            raise FileNotFoundError(f"File {p} not found")
            
        data = json.loads(p.read_text())
        return MixSnapshot(**data)

_default_service: Optional[AudioMixSnapshotService] = None

def get_audio_mix_snapshot_service() -> AudioMixSnapshotService:
    global _default_service
    if _default_service is None:
        _default_service = AudioMixSnapshotService()
    return _default_service
