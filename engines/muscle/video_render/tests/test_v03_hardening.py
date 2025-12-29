import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import engines.video_render.ffmpeg_runner as ffmpeg_runner
from engines.video_render.models import RenderPlan, PlanStep
from engines.video_render.ffmpeg_runner import run_ffmpeg, FFmpegError

class TestV03Hardening(unittest.TestCase):
    def test_gpu_detection(self):
        # Mock subprocess to return GPU encoders
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = """
 V..... h264_videotoolbox    VideoToolbox H.264 Encoder
 V..... h264_nvenc           NVIDIA NVENC H.264
            """
            ffmpeg_runner._HW_ENCODERS_CACHE = None
            encoders = ffmpeg_runner.get_available_hardware_encoders()
            self.assertIn("h264_videotoolbox", encoders)
            self.assertIn("h264_nvenc", encoders)
            self.assertNotIn("hevc_videotoolbox", encoders)

    def test_ffmpeg_runner_error_capture(self):
        plan = RenderPlan(
            output_path="/tmp/out.mp4",
            profile="social_1080p_h264",
            steps=[PlanStep(description="test", ffmpeg_args=["ffmpeg", "-i", "input"])]
        )
        
        with patch("subprocess.run") as mock_run:
            from subprocess import CalledProcessError
            err = CalledProcessError(1, ["ffmpeg"], stderr="Log line 1\nLog line 2\nFATAL ERROR")
            mock_run.side_effect = err
            
            with self.assertRaises(FFmpegError) as cm:
                run_ffmpeg(plan)
            
            self.assertIn("FATAL ERROR", str(cm.exception))
            self.assertIn("code 1", str(cm.exception))

    def test_ensure_proxies_stub(self):
        # Verify ensure_proxies logic (stubbed/simplified)
        from engines.video_render.service import RenderService
        # Mock dependencies
        mock_timeline = MagicMock()
        mock_media = MagicMock()
        
        # Setup mock project/sequence/clip
        mock_project = MagicMock()
        mock_project.sequence_ids = ["seq1"]
        mock_timeline.get_project.return_value = mock_project
        
        mock_seq = MagicMock()
        mock_seq.id = "seq1"
        mock_timeline.list_sequences_for_project.return_value = [mock_seq]
        
        mock_track = MagicMock()
        mock_track.id = "t1"
        mock_track.kind = "video"
        mock_timeline.list_tracks_for_sequence.return_value = [mock_track]
        
        mock_clip = MagicMock()
        mock_clip.asset_id = "a1"
        mock_timeline.list_clips_for_track.return_value = [mock_clip]
        
        # No proxy artifacts
        mock_media.list_artifacts_for_asset.return_value = []
        asset_path = Path(tempfile.mkdtemp()) / "asset.mp4"
        asset_path.write_bytes(b"video")
        mock_asset = MagicMock()
        mock_asset.id = "a1"
        mock_asset.tenant_id = "t_test"
        mock_asset.env = "dev"
        mock_asset.source_uri = str(asset_path)
        mock_asset.meta = {}
        mock_media.get_asset.return_value = mock_asset
        
        service = RenderService(job_repo=MagicMock())
        service.timeline_service = mock_timeline
        service.media_service = mock_media

        import engines.video_render.service as video_render_service
        original_ladder = video_render_service.PROXY_LADDER
        video_render_service.PROXY_LADDER = original_ladder[:1]
        try:
            count = service.ensure_proxies_for_project("p1")
            self.assertEqual(count, 1)  # Should detect 1 missing proxy

            # Now mock proxy existing
            mock_art = MagicMock()
            mock_art.kind = "video_proxy_360p"
            mock_art.meta = {
                "proxy_cache_key": f"{mock_asset.id}:video_proxy_360p:{mock_asset.source_uri}"
            }
            mock_media.list_artifacts_for_asset.return_value = [mock_art]

            count = service.ensure_proxies_for_project("p1")
            self.assertEqual(count, 0)  # Should be 0
        finally:
            video_render_service.PROXY_LADDER = original_ladder

    def test_hardware_encoder_resolution(self):
        from engines.video_render.service import RenderService
        service = RenderService(job_repo=MagicMock())
        service._hw_encoders = {"h264_nvenc"}
        service._force_cpu_enc = False
        self.assertEqual("h264_nvenc", service._resolve_hardware_encoder("social_1080p_h264"))
        service._force_cpu_enc = True
        self.assertEqual("libx264", service._resolve_hardware_encoder("social_1080p_h264"))

if __name__ == '__main__':
    unittest.main()
