import unittest
from io import BytesIO
from unittest.mock import patch

from PIL import Image

from engines.image_core.service import (
    ImageCoreService,
    SubjectDetectorUnavailable,
    SubjectDetectionFailure,
)
from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import MediaService, InMemoryMediaRepository, LocalMediaStorage


class _FakeDetector:
    def detect(self, image: Image.Image):
        return [(10, 10, 50, 50)]


class _EmptyDetector:
    def detect(self, image: Image.Image):
        return []


class TestSubjectCutout(unittest.TestCase):
    def setUp(self):
        repo = InMemoryMediaRepository()
        storage = LocalMediaStorage()
        self.media_service = MediaService(repo=repo, storage=storage)
        source = Image.new("RGB", (256, 256), "#222222")
        buffer = BytesIO()
        source.save(buffer, format="PNG")
        buffer.seek(0)
        upload_req = MediaUploadRequest(
            tenant_id="tenant",
            env="dev",
            kind="image",
            source_uri="pending",
            tags=["source"],
        )
        asset = self.media_service.register_upload(upload_req, "source.png", buffer.read())
        self.asset_id = asset.id

    def test_detect_subject_mask_creates_artifact_with_detector(self):
        detector = _FakeDetector()
        service = ImageCoreService(
            media_service=self.media_service, subject_detector=detector
        )
        mask_id = service.detect_subject_mask(
            self.asset_id, width=300, height=200, tenant_id="tenant", env="dev"
        )
        mask_art = self.media_service.get_artifact(mask_id)
        self.assertIsNotNone(mask_art)
        self.assertEqual(mask_art.meta.get("width"), 300)
        self.assertEqual(mask_art.meta.get("height"), 200)
        self.assertEqual(mask_art.meta.get("asset_id"), self.asset_id)
        self.assertEqual(mask_art.meta.get("model_used"), "opencv_haar_v1")
        self.assertEqual(mask_art.meta.get("detections"), 1)

        # Repeated calls should return cached artifact id
        second_mask = service.detect_subject_mask(
            self.asset_id, width=300, height=200, tenant_id="tenant", env="dev"
        )
        self.assertEqual(second_mask, mask_id)

    def test_detect_subject_mask_fails_when_detector_unavailable(self):
        service = ImageCoreService(media_service=self.media_service)
        with patch.object(
            ImageCoreService,
            "_ensure_subject_detector",
            side_effect=SubjectDetectorUnavailable("missing dependencies"),
        ):
            with self.assertRaises(SubjectDetectorUnavailable):
                service.detect_subject_mask(
                    self.asset_id, width=200, height=200, tenant_id="tenant", env="dev"
                )

    def test_detect_subject_mask_reports_failure_when_no_subjects(self):
        detector = _EmptyDetector()
        service = ImageCoreService(
            media_service=self.media_service, subject_detector=detector
        )
        with self.assertRaises(SubjectDetectionFailure):
            service.detect_subject_mask(
                self.asset_id, width=200, height=200, tenant_id="tenant", env="dev"
            )


if __name__ == "__main__":
    unittest.main()
