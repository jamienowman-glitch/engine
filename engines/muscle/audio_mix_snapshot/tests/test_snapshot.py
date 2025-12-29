import pytest
import json
from unittest.mock import MagicMock, patch
from engines.audio_mix_snapshot.service import AudioMixSnapshotService, CaptureRequest, DeltaRequest
from engines.audio_mix_snapshot.models import MixSnapshot, TrackState
from engines.media_v2.models import DerivedArtifact, MediaAsset

def test_capture_logic():
    mock_media = MagicMock()
    # Mock upload returning asset
    mock_media.register_upload.return_value = MediaAsset(
        id="up1", tenant_id="t", env="d", kind="other", source_uri="/tmp/snap1.json"
    )
    mock_media.register_artifact.return_value = DerivedArtifact(
        id="art1", parent_asset_id="up1", tenant_id="t", env="d", kind="audio_mix_snapshot", uri="/tmp/snap1.json"
    )
    
    svc = AudioMixSnapshotService(media_service=mock_media)
    
    # Input
    seq = {
        "tracks": [
            {"name": "Drums", "meta": {"gain_db": -6.0}},
            {"name": "Bass", "meta": {"gain_db": -3.0}},
        ]
    }
    
    req = CaptureRequest(tenant_id="t", env="d", audio_sequence=seq)
    
    snap = svc.capture_snapshot(req)
    
    assert "Drums" in snap.tracks
    assert snap.tracks["Drums"].gain_db == -6.0
    assert snap.complexity_score == 2

def test_compare_logic():
    mock_media = MagicMock()
    
    art_a = DerivedArtifact(id="a", parent_asset_id="p", tenant_id="t", env="d", kind="audio_mix_snapshot", uri="/tmp/a.json")
    art_b = DerivedArtifact(id="b", parent_asset_id="p", tenant_id="t", env="d", kind="audio_mix_snapshot", uri="/tmp/b.json")
    
    mock_media.get_artifact.side_effect = lambda uid: art_a if uid == "a" else art_b
    
    svc = AudioMixSnapshotService(media_service=mock_media)
    
    # Create snapshots
    snap_a = MixSnapshot(id="s1", tracks={
        "Drums": TrackState(name="Drums", gain_db=-6.0)
    })
    snap_b = MixSnapshot(id="s2", tracks={
        "Drums": TrackState(name="Drums", gain_db=-3.0), # Changed
        "Bass": TrackState(name="Bass", gain_db=0.0)    # Added
    })
    
    with patch("pathlib.Path.read_text") as mock_read:
        # Mock file reads
        # If path == /tmp/a.json return snap_a
        def read_side_effect():
            # How to distinguish? mock_read is on Path instance... 
            # but here patch is on class method or instance? 
            # It's hard to distinguish instance in side_effect of read_text unless we mock open.
            # Let's rely on patching _load_snapshot method for simpler test.
             pass
             
    # Easier: Patch _load_snapshot on sequence? No, patch on instance or class.
    with patch.object(AudioMixSnapshotService, "_load_snapshot") as mock_load:
        mock_load.side_effect = lambda art: snap_a if art.id == "a" else snap_b
        
        req = DeltaRequest(tenant_id="t", env="d", snapshot_a_id="a", snapshot_b_id="b")
        delta = svc.compare_snapshots(req)
        
        assert "Bass" in delta.added_tracks
        assert "Drums" in delta.changed_tracks
        assert delta.changed_tracks["Drums"]["gain_db"] == (-6.0, -3.0)
