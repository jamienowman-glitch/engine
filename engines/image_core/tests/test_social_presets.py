import unittest

from engines.image_core.service import ImageCoreService
from engines.media_v2.service import MediaService, InMemoryMediaRepository, LocalMediaStorage


class TestSocialThumbnailPresets(unittest.TestCase):
    def setUp(self):
        repo = InMemoryMediaRepository()
        storage = LocalMediaStorage()
        media_service = MediaService(repo=repo, storage=storage)
        self.service = ImageCoreService(media_service=media_service)

    def test_social_presets_dimensions_and_safe_title_box(self):
        expected_sizes = {
            "youtube_thumb_16_9": (1280, 720),
            "social_vertical_story_9_16": (1080, 1920),
            "social_square_1_1": (1080, 1080),
            "social_4_3_comfort": (1440, 1080),
        }

        for preset_id, (width, height) in expected_sizes.items():
            config = self.service.get_social_thumbnail_preset(preset_id)
            self.assertIsNotNone(config, f"{preset_id} should be defined")
            self.assertEqual(config["width"], width)
            self.assertEqual(config["height"], height)
            safe_box = config["safe_title_box"]
            self.assertEqual(safe_box["width"], int(width * 0.9))
            self.assertEqual(safe_box["height"], int(height * 0.8))
            self.assertEqual(safe_box["x"], int(width * 0.05))
            self.assertEqual(safe_box["y"], int(height * 0.1))
            self.assertAlmostEqual(safe_box["width_pct"], 0.9, places=6)
            self.assertAlmostEqual(safe_box["height_pct"], 0.8, places=6)
            self.assertEqual(safe_box["horizontal_margin_pct"], 0.05)
            self.assertEqual(safe_box["vertical_margin_pct"], 0.1)
            self.assertTrue(safe_box["centered"])
            self.assertEqual(config["format"], "PNG")
            self.assertEqual(config["recipe_id"], ImageCoreService.NO_CODE_MAN_RECIPE_ID)

    def test_list_social_thumbnail_presets_contains_all_ids(self):
        expected_ids = {
            "youtube_thumb_16_9",
            "social_vertical_story_9_16",
            "social_square_1_1",
            "social_4_3_comfort",
        }
        preset_ids = {preset["preset_id"] for preset in self.service.list_social_thumbnail_presets()}
        self.assertEqual(preset_ids, expected_ids)


if __name__ == "__main__":
    unittest.main()
