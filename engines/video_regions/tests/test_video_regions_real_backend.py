import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from engines.media_v2.models import DerivedArtifact


class TestRealRegionsBackend(unittest.TestCase):
    def setUp(self):
        import engines.video_regions.backend as backend_module

        self.backend_module = backend_module
        backend_module.cv2 = MagicMock()
        backend_module.np = MagicMock()
        backend_module.np.random = MagicMock()
        backend_module.np.random.seed.return_value = None
        self.original_has_opencv = backend_module.HAS_OPENCV
        backend_module.HAS_OPENCV = True
        self.backend_cls = backend_module.RealRegionsBackend
        self.detect_patcher = patch.object(
            self.backend_cls,
            "_detect_faces",
            return_value=[{"bbox": (10, 10, 50, 50), "confidence": 0.9, "time_ms": 0}],
        )
        self.write_mask_patcher = patch.object(
            self.backend_cls,
            "_write_mask",
            return_value=Path("/tmp/regions_mask.png"),
        )
        self.ensure_cascade_patcher = patch.object(self.backend_cls, "_ensure_cascade", return_value=None)
        self.detect_patcher.start()
        self.write_mask_patcher.start()
        self.ensure_cascade_patcher.start()
        self.backend = self.backend_cls()

    def tearDown(self):
        self.detect_patcher.stop()
        self.write_mask_patcher.stop()
        self.ensure_cascade_patcher.stop()
        self.backend_module.HAS_OPENCV = self.original_has_opencv

    def test_analyze_face_found(self):
        asset = MagicMock(spec=self.backend_module.MediaAsset)
        asset.id = "asset_1"
        asset.tenant_id = "t1"
        asset.env = "dev"
        asset.source_uri = "/tmp/fake.mp4"
        asset.meta = {"width": 128, "height": 128}
        asset.duration_ms = 1000
        req = MagicMock(spec=self.backend_module.AnalyzeRegionsRequest)
        req.include_regions = ["face"]
        req.tenant_id = "t1"
        req.env = "dev"
        req.asset_id = "asset_1"
        media_service = MagicMock()

        def register_artifact(r):
            return DerivedArtifact(
                id=f"art_{r.kind}",
                parent_asset_id=r.parent_asset_id,
                tenant_id=r.tenant_id,
                env=r.env,
                kind=r.kind,
                uri=r.uri,
                meta=r.meta,
            )

        media_service.register_artifact.side_effect = register_artifact
        result = self.backend.analyze(asset, req, media_service, cache_key="cache_1")

        self.assertEqual(result.summary_artifact_id, "art_video_region_summary")
        self.assertEqual(result.summary.meta["cache_key"], "cache_1")
        self.assertEqual(result.summary.entries[0].region, "face")
        self.assertEqual(result.summary.entries[0].mask_artifact_id, "art_mask")
        self.assertEqual(media_service.register_artifact.call_count, 2)
