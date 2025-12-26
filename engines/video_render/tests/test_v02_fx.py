
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from engines.video_timeline.models import Clip, Filter, FilterStack
from engines.video_render.planner import build_transition_plans
from engines.video_render.service import RenderService
from engines.video_presets.service import _built_in_filter_presets
from engines.media_v2.service import set_media_service, MediaService, InMemoryMediaRepository, LocalMediaStorage
from engines.video_timeline.service import set_timeline_service, TimelineService, InMemoryTimelineRepository

class TestV02Features(unittest.TestCase):
    def setUp(self):
        self.media_service = MediaService(repo=InMemoryMediaRepository(), storage=LocalMediaStorage())
        self.timeline_service = TimelineService(repo=InMemoryTimelineRepository())
        set_media_service(self.media_service)
        set_timeline_service(self.timeline_service)

    def test_filter_chain_extended(self):
        service = RenderService(job_repo=MagicMock())

        # Test new filters
        stack = FilterStack(
            tenant_id="t1",
            env="test",
            target_type="clip",
            target_id="c1",
            filters=[
                Filter(type="sharpen", params={"luma_amount": 1.0}),
                Filter(type="vignette", params={"angle": 0.5}),
                Filter(type="hue_shift", params={"shift": 90}),
                Filter(type="film_grain", params={"strength": 20}),
                Filter(type="gamma", params={"gamma": 2.0}),
                Filter(type="bloom", params={"intensity": 0.5}),
            ],
        )

        chain = service._filter_chain(stack)
        expected = [
            "unsharp=3:3:1.0",
            "vignette=angle=0.5:softness=0.5:strength=0.8",
            "hue=h=90.0",
            "noise=alls=20.0:allf=t+u",
            "eq=gamma=2.0",
            "boxblur=luma_radius=15:luma_power=1:chroma_radius=0:chroma_power=1",
        ]
        self.assertEqual(chain, expected)

    def test_presets_exist(self):
        presets = _built_in_filter_presets()
        names = [p.name for p in presets]
        self.assertIn("style_cinematic", names)
        self.assertIn("style_vlog", names)
        self.assertIn("style_punchy", names)
        self.assertIn("style_monochrome", names)

    def test_profile_audio_bitrate(self):
        service = RenderService(job_repo=MagicMock())
        args = service._profile_args("social_1080p_h264")
        self.assertIn("-b:a", args)
        self.assertIn("192k", args)
        self.assertIn("-threads", args)
        self.assertIn("4", args)

        args_prev = service._profile_args("preview_720p_fast")
        self.assertIn("-b:a", args_prev)
        self.assertIn("128k", args_prev)

    def test_transition_catalog_aliases(self):
        clip_a = Clip(
            tenant_id="t1",
            env="dev",
            track_id="t1",
            asset_id="a1",
            in_ms=0,
            out_ms=1000,
            start_ms_on_timeline=0,
        )
        clip_b = Clip(
            tenant_id="t1",
            env="dev",
            track_id="t1",
            asset_id="a1",
            in_ms=0,
            out_ms=1000,
            start_ms_on_timeline=1000,
        )
        transition = SimpleNamespace(
            id="trans1",
            tenant_id="t1",
            env="dev",
            sequence_id="seq1",
            type="slide_up",
            duration_ms=500,
            from_clip_id=clip_a.id,
            to_clip_id=clip_b.id,
            meta={}  # Added meta
        )
        plans = build_transition_plans([transition], {clip_a.id: clip_a, clip_b.id: clip_b})
        self.assertEqual(len(plans), 1)
        plan = plans[0]
        self.assertEqual(plan.video_alias, "slideup")
        self.assertEqual(plan.audio_alias, "acrossfade")
        self.assertIn("xfade=transition=slideup", plan.video_filter)

    def test_invalid_filter_raises(self):
        service = RenderService(job_repo=MagicMock())
        stack = FilterStack(
            tenant_id="t1",
            env="dev",
            user_id="u1",
            target_type="clip",
            target_id="clip1",
            filters=[Filter(type="unknown_filter")],
        )
        with self.assertRaises(ValueError):
            service._filter_chain(stack)

    def test_invalid_transition_type_raises(self):
        clip_a = Clip(
            tenant_id="t1",
            env="dev",
            track_id="t1",
            asset_id="a1",
            in_ms=0,
            out_ms=1000,
            start_ms_on_timeline=0,
        )
        clip_b = Clip(
            tenant_id="t1",
            env="dev",
            track_id="t1",
            asset_id="a1",
            in_ms=0,
            out_ms=1000,
            start_ms_on_timeline=1000,
        )
        transition = SimpleNamespace(
            id="trans2",
            tenant_id="t1",
            env="dev",
            sequence_id="seq1",
            type="spin",
            duration_ms=500,
            from_clip_id=clip_a.id,
            to_clip_id=clip_b.id,
            meta={} # Added meta
        )
        with self.assertRaises(ValueError):
            build_transition_plans([transition], {clip_a.id: clip_a, clip_b.id: clip_b})


if __name__ == "__main__":
    unittest.main()
