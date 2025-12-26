import io
import unittest
from unittest.mock import patch

from PIL import Image

from engines.image_core.service import ImageCoreService
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest
from engines.media_v2.service import MediaService, InMemoryMediaRepository, LocalMediaStorage
from engines.typography_core.renderer import TextLayoutMetadata
from engines.typography_core.service import TypographyService


class _FakeDetector:
    def detect(self, image: Image.Image):
        return [(10, 10, 200, 400)]


class _FakeGenerativeFillProvider:
    def __init__(self):
        self.called_with = None

    def expand(self, image: Image.Image, width: int, height: int, margin_x: int, margin_y: int) -> Image.Image:
        self.called_with = (width, height, margin_x, margin_y)
        expanded_width = width + margin_x * 2
        expanded_height = height + margin_y * 2
        canvas = Image.new("RGBA", (expanded_width, expanded_height), (12, 34, 56, 255))
        canvas.paste(image, (margin_x, margin_y))
        return canvas


class TestRecipeNoCodeThumb(unittest.TestCase):
    def setUp(self):
        repo = InMemoryMediaRepository()
        storage = LocalMediaStorage()
        self.media_service = MediaService(repo=repo, storage=storage)
        base_img = Image.new("RGB", (1920, 1080), "#333333")
        buffer = io.BytesIO()
        base_img.save(buffer, format="PNG")
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

        text_img = Image.new("RGBA", (300, 120), (255, 255, 255, 255))
        text_buffer = io.BytesIO()
        text_img.save(text_buffer, format="PNG")
        text_buffer.seek(0)
        text_req = MediaUploadRequest(
            tenant_id="tenant",
            env="dev",
            kind="image",
            source_uri="pending",
            tags=["text"],
        )
        self.text_asset = self.media_service.register_upload(
            text_req, "text.png", text_buffer.read()
        )
        artifact = self.media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id="tenant",
                env="dev",
                parent_asset_id=self.text_asset.id,
                kind="image_render",
                uri=self.text_asset.source_uri,
                meta={"width": text_img.width, "height": text_img.height},
            )
        )
        self.text_artifact_id = artifact.id
        self.text_meta = TextLayoutMetadata(
            font_family="Inter",
            font_id="test",
            font_path="/fake",
            font_size_px=60,
            font_preset="regular",
            variation_axes={},
            tracking=0,
            alignment="center",
            width=text_img.width,
            height=text_img.height,
            line_height_px=45.0,
            line_count=1,
            layout_hash="text_hash",
        )

        self.typography_service = TypographyService(media_service=self.media_service)
        self.service = ImageCoreService(
            media_service=self.media_service,
            subject_detector=_FakeDetector(),
            typography_service=self.typography_service,
        )

    def _patch_text_render(self):
        return patch.object(
            self.typography_service,
            "render_text_with_metadata",
            return_value=(self.text_artifact_id, self.text_asset.id, self.text_meta),
        )

    def test_plan_applies_adjustments_and_mask(self):
        preset = self.service.get_social_thumbnail_preset("youtube_thumb_16_9")
        with self._patch_text_render():
            mask_id = self.service.detect_subject_mask(
                self.asset_id, preset["width"], preset["height"], "tenant", "dev"
            )
            composition = self.service._plan_social_thumbnail_composition(
                self.asset_id,
                preset,
                mask_id,
                self.text_asset.id,
                self.text_meta,
                bw_background=True,
                tenant_id="tenant",
                env="dev",
            )

        bg_layer = composition.layers[0]
        fg_layer = composition.layers[1]
        text_layer = composition.layers[2]

        self.assertEqual(bg_layer.filter_mode, "blur")
        self.assertEqual(bg_layer.adjustments.saturation, 0.0)
        self.assertEqual(fg_layer.mask_artifact_id, mask_id)
        self.assertEqual(text_layer.asset_id, self.text_asset.id)

    def test_recipe_metadata_and_extend_canvas(self):
        preset_id = "youtube_thumb_16_9"
        preset = self.service.get_social_thumbnail_preset(preset_id)
        with self._patch_text_render():
            artifact = self.service.create_social_thumbnail(
                self.asset_id,
                title="NO CODE MAN",
                preset_id=preset_id,
                tenant_id="tenant",
                env="dev",
                extend_canvas=False,
            )

        self.assertEqual(artifact.meta["preset_id"], preset_id)
        self.assertEqual(artifact.meta["recipe_id"], ImageCoreService.NO_CODE_MAN_RECIPE_ID)
        self.assertTrue(artifact.meta.get("subject_mask_id"))
        self.assertEqual(artifact.meta["safe_title_box"]["width"], int(artifact.meta["width"] * 0.9))

        with self._patch_text_render():
            extended = self.service.create_social_thumbnail(
                self.asset_id,
                title="NO CODE MAN",
                preset_id=preset_id,
                tenant_id="tenant",
                env="dev",
                extend_canvas=True,
            )

        self.assertGreater(extended.meta["width"], preset["width"])
        self.assertGreater(extended.meta["height"], preset["height"])
        self.assertGreater(extended.meta["safe_title_box"]["width"], preset["safe_title_box"]["width"])

    def test_extend_canvas_generative_fill_mode_uses_provider(self):
        provider = _FakeGenerativeFillProvider()
        service = ImageCoreService(
            media_service=self.media_service,
            subject_detector=_FakeDetector(),
            typography_service=self.typography_service,
            generative_fill_provider=provider,
        )
        preset_id = "youtube_thumb_16_9"
        preset = service.get_social_thumbnail_preset(preset_id)
        with self._patch_text_render():
            artifact = service.create_social_thumbnail(
                self.asset_id,
                title="FUTURE FILL",
                preset_id=preset_id,
                tenant_id="tenant",
                env="dev",
                extend_canvas=True,
                extend_canvas_mode="generative_fill",
            )

        self.assertTrue(provider.called_with)
        width, height, margin_x, margin_y = provider.called_with
        self.assertEqual(width, preset["width"])
        self.assertEqual(height, preset["height"])
        expected_width = width + margin_x * 2
        expected_height = height + margin_y * 2
        self.assertEqual(artifact.meta["width"], expected_width)
        self.assertEqual(artifact.meta["height"], expected_height)
