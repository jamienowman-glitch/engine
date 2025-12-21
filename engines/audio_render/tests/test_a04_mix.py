import unittest
from unittest.mock import MagicMock
from engines.audio_timeline.models import AudioSequence, AudioClip, AudioTrack, AutomationPoint
from engines.audio_render.planner import build_ffmpeg_mix_plan

class TestA04Mix(unittest.TestCase):
    def test_fade_curves_in_planner(self):
        seq = AudioSequence(tenant_id="t", env="e")
        clip = AudioClip(
            asset_id="asset1", # Need ID to lookup
            start_ms=0, duration_ms=5000, 
            fade_in_ms=500, fade_out_ms=500, fade_curve="exp"
        )
        track = AudioTrack(clips=[clip])
        seq.tracks.append(track)
        
        media_service = MagicMock()
        media_service.get_asset.return_value = MagicMock(source_uri="test.wav")
        
        inputs, filters, _, metadata = build_ffmpeg_mix_plan(seq, media_service)
        
        self.assertIn("afade=t=in:st=0:d=0.5:curve=exp", filters)
        self.assertIn("afade=t=out", filters)
        self.assertIn(":curve=exp", filters)
        self.assertIn("master", metadata)
        self.assertEqual(metadata["master"]["export_preset"], "default")
        self.assertFalse(metadata["master"]["dithered"])

    def test_export_preset_limiter(self):
        seq = AudioSequence(tenant_id="t", env="e")
        # Need at least one clip to trigger master chain
        clip = AudioClip(asset_id="a1", start_ms=0, duration_ms=1000)
        seq.tracks.append(AudioTrack(clips=[clip]))
        
        ms = MagicMock()
        ms.get_asset.return_value = MagicMock(source_uri="in.wav")
        
        inputs, filters, _, metadata = build_ffmpeg_mix_plan(seq, ms, export_preset="podcast")
        # Should see limit=-1.0dB
        self.assertIn("limit=-1.0dB", filters)
        self.assertEqual(metadata["master"]["limiter_thresh"], -1.0)
        self.assertEqual(metadata["master"]["export_preset"], "podcast")
        self.assertEqual(metadata["master"]["roles"], ["master"])

    def test_unknown_export_preset_raises(self):
        seq = AudioSequence(tenant_id="t", env="e")
        clip = AudioClip(asset_id="a1", start_ms=0, duration_ms=1000)
        seq.tracks.append(AudioTrack(clips=[clip]))
        ms = MagicMock()
        ms.get_asset.return_value = MagicMock(source_uri="in.wav")
        with self.assertRaises(ValueError):
            build_ffmpeg_mix_plan(seq, ms, export_preset="alien_preset")

    def test_stems_generation_plan(self):
        # This test ensures planner maps output correctly, service test verifies execution
        seq = AudioSequence(tenant_id="t", env="e")
        inputs, filters, outputs, metadata = build_ffmpeg_mix_plan(seq, MagicMock())
        self.assertIn("master", outputs)
        self.assertIn("master", metadata)
        self.assertEqual(metadata["master"]["bus_id"], "master")

    def test_automation_includes_volume_expression(self):
        seq = AudioSequence(tenant_id="t", env="e")
        clip = AudioClip(
            asset_id="asset1",
            start_ms=0,
            duration_ms=500,
            gain_db=0.0,
            automation={"gain": [AutomationPoint(time_ms=0, value=-3.0), AutomationPoint(time_ms=500, value=0.0)]}
        )
        track = AudioTrack(clips=[clip])
        seq.tracks.append(track)
        ms = MagicMock()
        ms.get_asset.return_value = MagicMock(source_uri="file.wav")

        _, filters, _, _ = build_ffmpeg_mix_plan(seq, ms)
        self.assertIn("volume=pow(10,", filters)

if __name__ == '__main__':
    unittest.main()
