import pytest
from unittest.mock import MagicMock, patch, ANY
from engines.audio_render.service import AudioRenderService, RenderRequest
from engines.audio_timeline.service import AudioTimelineService
from engines.media_v2.models import DerivedArtifact, MediaAsset
from engines.audio_mix_buses.models import MixGraph, BusConfig

def test_render_plan_with_graph():
    from engines.audio_render.planner import build_ffmpeg_mix_plan
    
    tl = AudioTimelineService()
    seq = tl.create_sequence("t1", "d")
    
    # Track "Drums" -> should go to bus_drums
    t_drums = tl.add_track(seq, "Drums")
    tl.add_clip(t_drums, 0, asset_id="k1", duration_ms=1000)
    
    # Track "Keys" -> should go to bus_inst (Music)
    t_keys = tl.add_track(seq, "Keys")
    tl.add_clip(t_keys, 0, asset_id="p1", duration_ms=1000)
    
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(id="a", tenant_id="t", env="d", kind="audio", source_uri="/tmp/f.wav")
    
    graph = MixGraph(id="g", name="G", buses=[
        BusConfig(id="bus_drums", name="D", roles=["drums"]),
        BusConfig(id="bus_inst", name="M", roles=["keys"])
    ])
    
    inputs, flt, maps, metadata = build_ffmpeg_mix_plan(seq, mock_media, graph)
    
    # Check filter
    # Expect nodes from maps to be in filter
    assert maps["bus_drums"] in flt
    assert maps["bus_inst"] in flt
    
    # Check maps keys
    assert "bus_drums" in maps
    assert "bus_inst" in maps
    assert "master" in maps
    assert metadata["bus_drums"]["roles"] == ["drums"]

def test_render_execution_stems():
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(id="a", tenant_id="t", env="d", kind="audio", source_uri="/tmp/a.wav")
    
    # Mock upload: needs to return MediaAsset for each call
    def fake_upload(req, filename, content):
        return MediaAsset(id=f"asset_{filename}", tenant_id="t", env="d", kind="audio", source_uri=f"/tmp/{filename}")
    mock_media.register_upload.side_effect = fake_upload
    
    mock_media.register_artifact.side_effect = lambda r: DerivedArtifact(id=f"art_{r.kind}", parent_asset_id="p", tenant_id="t", env="d", kind=r.kind, uri="u")
    
    with patch("subprocess.run") as mock_run, \
         patch("engines.audio_render.service.Path") as mock_path, \
         patch("engines.audio_render.service.get_audio_mix_buses_service") as mock_get_buses:
         
        # Mock Path
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.read_bytes.return_value = b"data"
        
        # Mock Bus Service
        mock_bus_svc = MagicMock()
        mock_bus_svc.get_mix_graph.return_value = MixGraph(id="g", name="G", buses=[
            BusConfig(id="bus_drums", name="D", roles=["drums"])
        ])
        mock_get_buses.return_value = mock_bus_svc
         
        svc = AudioRenderService(media_service=mock_media)
        
        tl = AudioTimelineService()
        seq = tl.create_sequence("t1", "d")
        t = tl.add_track(seq, "Drums")
        tl.add_clip(t, 0, asset_id="k1")
        
        req = RenderRequest(
            sequence=seq,
            mix_preset_id="default_mix",
            stems_export=True
        )
        
        svc.render_sequence(req)
        
        # Verify Command
        args, _ = mock_run.call_args
        cmd = args[0]
        
        # Should have multiple maps
        # -map [out] ... render_xxx.wav
        # -map [bus_drums_out] ... stem_bus_drums_xxx.wav
        
        # Count "-map" occurrences
        map_count = cmd.count("-map")
        assert map_count == 2 # Master + 1 Stem
        
        # Verify registration calls
        # 1 render, 1 stem -> 2 uploads
        assert mock_media.register_upload.call_count == 2
        # Verify artifact kinds
        kinds = [c.kwargs['kind'] if 'kind' in c.kwargs else c.args[0].kind for c in mock_media.register_artifact.call_args_list]
        assert "audio_render" in kinds
        assert "audio_bus_stem" in kinds
        master_call = mock_media.register_artifact.call_args_list[0]
        master_meta = master_call.args[0].meta
        assert master_meta["bus_id"] == "master"
        assert master_meta["export_preset"] == "default"
        assert master_meta["roles"] == ["master"]

        stem_call = mock_media.register_artifact.call_args_list[1]
        stem_meta = stem_call.args[0].meta
        assert stem_meta["bus_id"] == "bus_drums"
        assert stem_meta["roles"] == ["drums"]
        assert stem_meta["export_preset"] == "default"
        assert stem_meta["gain_db"] == 0.0

