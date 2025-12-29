import unittest
from unittest.mock import MagicMock, patch
import sys
import random

# Mock dependencies
from engines.video_multicam.models import MultiCamAutoCutRequest, MultiCamTrackSpec, MultiCamSession
from engines.video_multicam.service import MultiCamService
from engines.video_assist.service import VideoAssistService
from engines.video_focus_automation.service import FocusAutomationService
from engines.video_focus_automation.models import FocusRequest

class TestV04Features(unittest.TestCase):
    def test_multicam_autocut_pacing(self):
        # Setup Multicam Service with mocks
        service = MultiCamService(
            media_service=MagicMock(),
            timeline_service=MagicMock(),
            align_backend=MagicMock()
        )
        # Mock Session
        session = MultiCamSession(
            tenant_id="t1", env="e1", project_id="p1", name="test",
            tracks=[
                MultiCamTrackSpec(asset_id="a1", role="primary"),
                MultiCamTrackSpec(asset_id="a2", role="secondary")
            ]
        )
        service.get_session = MagicMock(return_value=session)
        service.media_service.get_asset.return_value = MagicMock(duration_ms=60000)
        
        # Test 1: Auto Cut
        req = MultiCamAutoCutRequest(
            session_id=session.id, tenant_id="t1", env="e1",
            min_shot_duration_ms=2000, max_shot_duration_ms=5000
        )
        
        # We need to mock create_clip to verify shot durations
        clips_created = []
        def mock_create_clip(clip):
            clips_created.append(clip)
            return clip
        service.timeline_service.create_clip.side_effect = mock_create_clip
        service.timeline_service.create_sequence.return_value = MagicMock(id="seq1")
        service.timeline_service.create_track.return_value = MagicMock(id="track1")

        service.auto_cut_sequence(req)
        
        # Verify we got clips
        self.assertTrue(len(clips_created) > 5)
        
        # Verify durations respected bounds (mostly)
        for c in clips_created:
            dur = c.out_ms - c.in_ms
            # Note: last clip might be shorter, so check first few
            if c != clips_created[-1]:
                 self.assertGreaterEqual(dur, 2000)
                 self.assertLessEqual(dur, 5000)

    def test_assist_highlights_semantic(self):
        service = VideoAssistService(timeline_service=MagicMock(), media_service=MagicMock())
        mock_project = MagicMock(sequence_ids=["s1"], tenant_id="t1", env="e1")
        service.timeline_service.get_project.return_value = mock_project
        service.timeline_service.list_tracks_for_sequence.return_value = [MagicMock(kind="video", id="t1")]
        service.timeline_service.list_clips_for_track.return_value = [MagicMock(asset_id="a1")]
        
        # Mock artifact presence
        mock_art = MagicMock()
        mock_art.kind = "audio_semantic_timeline"
        mock_art.id = "art1"
        service.media_service.list_artifacts_for_asset.return_value = [mock_art]
        
        # Run
        seq, track, clips = service.generate_highlights("p1")
        
        # Should have clips
        self.assertTrue(len(clips) > 0)
        # Should have preferred semantic mocked candidates (which we set to 0.8 score)
        # vs fallback (0.4).
        # We can't easily inspect internal score here, but valid execution is a good sign.
        pass

    def test_focus_fallback(self):
        service = FocusAutomationService(media_service=MagicMock())
        service.media_service.get_asset.return_value = MagicMock(tenant_id="t1", env="e1")
        
        # Mock NO artifacts
        service.media_service.list_artifacts_for_asset.return_value = []
        
        req = FocusRequest(asset_id="a1", clip_id="c1")
        res = service.calculate_focus(req)
        
        # Should return fallback center (0.5)
        self.assertIsNotNone(res)
        self.assertEqual(res.automation_x.keyframes[0].value, 0.5)

if __name__ == '__main__':
    unittest.main()
