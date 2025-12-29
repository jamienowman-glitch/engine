import unittest
from unittest.mock import MagicMock, patch
from engines.audio_fx_chain.presets import FX_PRESETS, FX_PRESET_METADATA
from engines.audio_fx_chain.dsp import build_ffmpeg_filter_string
from engines.audio_groove.dsp import extract_groove_offsets
from engines.audio_resample.service import AudioResampleService
from engines.audio_resample.models import ResampleRequest

class TestA03Creative(unittest.TestCase):
    def test_new_presets(self):
        # Verify tape_warmth exists and builds string
        self.assertIn("tape_warmth", FX_PRESETS)
        params = FX_PRESETS["tape_warmth"]
        chain = build_ffmpeg_filter_string(params)
        self.assertIn("highpass=f=40", chain)
        self.assertIn("lowpass=f=16000", chain)

    def test_preset_metadata_surface(self):
        meta = FX_PRESET_METADATA["delay_dream"]
        self.assertEqual(meta["latency_ms"], 30)
        self.assertAlmostEqual(meta["intensity"], 0.5)

    def test_saturation_sizzle_chain(self):
        params = FX_PRESETS["saturation_sizzle"]
        chain = build_ffmpeg_filter_string(params)
        self.assertIn("highpass=f=80", chain)
        self.assertIn("lowpass=f=12000", chain)

    def test_groove_robustness(self):
        # Test empty onsets handling
        mock_librosa = MagicMock()
        mock_librosa.load.return_value = (MagicMock(), 22050)
        mock_librosa.onset.onset_detect.return_value = []
        mock_librosa.frames_to_time.return_value = []
        
        with patch.dict("sys.modules", {"librosa": mock_librosa, "librosa.onset": MagicMock()}):
             offsets = extract_groove_offsets("dummy.wav", 120, 16)
             self.assertEqual(len(offsets), 16)
             self.assertEqual(offsets[0], 0.0)

    def test_resample_quality_flag(self):
        service = AudioResampleService(media_service=MagicMock())
        # Mock source artifact
        mock_art = MagicMock(uri="in.wav", parent_asset_id="asset1", start_ms=0, end_ms=1000)
        service.media_service.get_artifact.return_value = mock_art
        
        # Mock upload response
        mock_asset = MagicMock(source_uri="gs://bucket/out.wav")
        mock_asset.id = "asset2"
        service.media_service.register_upload.return_value = mock_asset
        
        mock_derived = MagicMock(uri="gs://bucket/out.wav", parent_asset_id="asset2")
        mock_derived.id = "art_resampled"
        service.media_service.register_artifact.return_value = mock_derived
        
        req = ResampleRequest(
            tenant_id="t1", env="e1", artifact_id="art1",
            target_bpm=120, quality_preset="high"
        )
        
        with patch("subprocess.run") as mock_run:
            with patch("pathlib.Path.read_bytes", return_value=b"data"):
                service.resample_artifact(req)
                
                # Check args for -resampler soxr
                args = mock_run.call_args[0][0]
                self.assertIn("-resampler", args)
                self.assertIn("soxr", args)

if __name__ == '__main__':
    unittest.main()
