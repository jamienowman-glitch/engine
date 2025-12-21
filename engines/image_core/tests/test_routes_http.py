"""Tests for image_core HTTP routes."""

import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
import io
from PIL import Image

from engines.image_core.routes import router
from engines.image_core.models import ImageComposition, ImageLayer
from engines.image_core.service import ImageCoreService
from engines.media_v2.models import DerivedArtifact
from engines.media_v2.service import MediaService, InMemoryMediaRepository, LocalMediaStorage


class TestImageCoreRoutes(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
        
        # Real service with in-memory repo
        repo = InMemoryMediaRepository()
        storage = LocalMediaStorage()
        media_svc = MediaService(repo=repo, storage=storage)
        self.service = ImageCoreService(media_service=media_svc)
        
        # Patch get_image_core_service to return our service
        self.patcher = patch(
            'engines.image_core.routes.get_image_core_service',
            return_value=self.service
        )
        self.mock_get_service = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_list_presets(self):
        """Test GET /image/presets returns all presets."""
        response = self.client.get("/image/presets")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("presets", data)
        self.assertIn("total_count", data)
        self.assertGreater(len(data["presets"]), 0)
        
        # Check that presets have expected fields
        preset = data["presets"][0]
        self.assertIn("preset_id", preset)
        self.assertIn("format", preset)
        self.assertIn("category", preset)

    def test_render_composition_valid(self):
        """Test POST /image/render with valid composition."""
        payload = {
            "tenant_id": "t_test",
            "env": "dev",
            "composition": {
                "width": 400,
                "height": 400,
                "background_color": "#FFFFFF",
                "layers": [
                    {
                        "name": "bg",
                        "color": "#FF0000FF",
                        "width": 400,
                        "height": 400,
                        "x": 0,
                        "y": 0,
                    }
                ],
            },
            "preset_id": "thumbnail_200",
        }
        
        response = self.client.post("/image/render", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("artifact_id", data)
        self.assertIn("format", data)
        self.assertEqual(data["preset_id"], "thumbnail_200")

    def test_render_composition_no_preset(self):
        """Test POST /image/render without preset (defaults to PNG)."""
        payload = {
            "tenant_id": "t_test",
            "env": "test",
            "composition": {
                "width": 512,
                "height": 512,
                "background_color": "#000000",
                "layers": [
                    {
                        "color": "#00FF00FF",
                        "width": 256,
                        "height": 256,
                        "x": 128,
                        "y": 128,
                    }
                ],
            },
        }
        
        response = self.client.post("/image/render", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("artifact_id", data)
        self.assertEqual(data["format"], "PNG")
        self.assertIsNone(data["preset_id"])

    def test_render_composition_invalid_env(self):
        """Test POST /image/render with invalid env."""
        payload = {
            "tenant_id": "t_test",
            "env": "invalid_env",
            "composition": {
                "width": 100,
                "height": 100,
                "layers": [],
            },
        }
        
        response = self.client.post("/image/render", json=payload)
        self.assertEqual(response.status_code, 422)  # Validation error

    def test_render_composition_missing_tenant(self):
        """Test POST /image/render with missing tenant_id."""
        payload = {
            "env": "dev",
            "composition": {
                "width": 100,
                "height": 100,
                "layers": [],
            },
        }
        
        response = self.client.post("/image/render", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_batch_render_composition(self):
        """Test POST /image/batch-render with multiple presets."""
        payload = {
            "tenant_id": "t_test",
            "env": "test",
            "composition": {
                "width": 1000,
                "height": 1000,
                "background_color": "#EEEEEE",
                "layers": [
                    {
                        "color": "#3366CCFF",
                        "width": 1000,
                        "height": 1000,
                    }
                ],
            },
            "preset_ids": ["instagram_1080", "thumbnail_200", "web_small"],
        }
        
        response = self.client.post("/image/batch-render", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("results", data)
        self.assertIn("total_count", data)
        self.assertGreater(len(data["results"]), 0)
        
        # Check that all presets returned results
        for preset_id in payload["preset_ids"]:
            if preset_id in data["results"]:
                result = data["results"][preset_id]
                self.assertIn("artifact_id", result)
                self.assertEqual(result["preset_id"], preset_id)

    def test_batch_render_empty_presets(self):
        """Test POST /image/batch-render with empty preset list."""
        payload = {
            "tenant_id": "t_test",
            "env": "test",
            "composition": {
                "width": 100,
                "height": 100,
                "layers": [],
            },
            "preset_ids": [],
        }
        
        response = self.client.post("/image/batch-render", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_batch_render_too_many_presets(self):
        """Test POST /image/batch-render with too many presets."""
        payload = {
            "tenant_id": "t_test",
            "env": "test",
            "composition": {
                "width": 100,
                "height": 100,
                "layers": [],
            },
            "preset_ids": [f"preset_{i}" for i in range(25)],
        }
        
        response = self.client.post("/image/batch-render", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_render_with_parent_asset(self):
        """Test POST /image/render with parent_asset_id."""
        payload = {
            "tenant_id": "t_test",
            "env": "dev",
            "composition": {
                "width": 200,
                "height": 200,
                "layers": [
                    {"color": "#FF00FFFF", "width": 200, "height": 200}
                ],
            },
            "parent_asset_id": "asset_parent_123",
        }
        
        response = self.client.post("/image/render", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("artifact_id", data)

if __name__ == '__main__':
    unittest.main()

    def test_list_presets(self):
        """Test GET /image/presets returns all presets."""
        response = self.client.get("/image/presets")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("presets", data)
        self.assertIn("total_count", data)
        self.assertGreater(len(data["presets"]), 0)
        
        # Check that presets have expected fields
        preset = data["presets"][0]
        self.assertIn("preset_id", preset)
        self.assertIn("format", preset)
        self.assertIn("category", preset)

    def test_render_composition_valid(self):
        """Test POST /image/render with valid composition."""
        payload = {
            "tenant_id": "t_test",
            "env": "dev",
            "composition": {
                "width": 400,
                "height": 400,
                "background_color": "#FFFFFF",
                "layers": [
                    {
                        "name": "bg",
                        "color": "#FF0000FF",
                        "width": 400,
                        "height": 400,
                        "x": 0,
                        "y": 0,
                    }
                ],
            },
            "preset_id": "thumbnail_200",
        }
        
        response = self.client.post("/image/render", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("artifact_id", data)
        self.assertIn("format", data)
        self.assertEqual(data["preset_id"], "thumbnail_200")

    def test_render_composition_no_preset(self):
        """Test POST /image/render without preset (defaults to PNG)."""
        payload = {
            "tenant_id": "t_test",
            "env": "test",
            "composition": {
                "width": 512,
                "height": 512,
                "background_color": "#000000",
                "layers": [
                    {
                        "color": "#00FF00FF",
                        "width": 256,
                        "height": 256,
                        "x": 128,
                        "y": 128,
                    }
                ],
            },
        }
        
        response = self.client.post("/image/render", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("artifact_id", data)
        self.assertEqual(data["format"], "PNG")
        self.assertIsNone(data["preset_id"])

    def test_render_composition_invalid_env(self):
        """Test POST /image/render with invalid env."""
        payload = {
            "tenant_id": "t_test",
            "env": "invalid_env",
            "composition": {
                "width": 100,
                "height": 100,
                "layers": [],
            },
        }
        
        response = self.client.post("/image/render", json=payload)
        self.assertEqual(response.status_code, 422)  # Validation error

    def test_render_composition_missing_tenant(self):
        """Test POST /image/render with missing tenant_id."""
        payload = {
            "env": "dev",
            "composition": {
                "width": 100,
                "height": 100,
                "layers": [],
            },
        }
        
        response = self.client.post("/image/render", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_batch_render_composition(self):
        """Test POST /image/batch-render with multiple presets."""
        payload = {
            "tenant_id": "t_test",
            "env": "test",
            "composition": {
                "width": 1000,
                "height": 1000,
                "background_color": "#EEEEEE",
                "layers": [
                    {
                        "color": "#3366CCFF",
                        "width": 1000,
                        "height": 1000,
                    }
                ],
            },
            "preset_ids": ["instagram_1080", "thumbnail_200", "web_small"],
        }
        
        response = self.client.post("/image/batch-render", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("results", data)
        self.assertIn("total_count", data)
        self.assertGreater(len(data["results"]), 0)
        
        # Check that all presets returned results
        for preset_id in payload["preset_ids"]:
            if preset_id in data["results"]:
                result = data["results"][preset_id]
                self.assertIn("artifact_id", result)
                self.assertEqual(result["preset_id"], preset_id)

    def test_batch_render_empty_presets(self):
        """Test POST /image/batch-render with empty preset list."""
        payload = {
            "tenant_id": "t_test",
            "env": "test",
            "composition": {
                "width": 100,
                "height": 100,
                "layers": [],
            },
            "preset_ids": [],
        }
        
        response = self.client.post("/image/batch-render", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_batch_render_too_many_presets(self):
        """Test POST /image/batch-render with too many presets."""
        payload = {
            "tenant_id": "t_test",
            "env": "test",
            "composition": {
                "width": 100,
                "height": 100,
                "layers": [],
            },
            "preset_ids": [f"preset_{i}" for i in range(25)],
        }
        
        response = self.client.post("/image/batch-render", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_render_with_parent_asset(self):
        """Test POST /image/render with parent_asset_id."""
        payload = {
            "tenant_id": "t_test",
            "env": "dev",
            "composition": {
                "width": 200,
                "height": 200,
                "layers": [
                    {"color": "#FF00FFFF", "width": 200, "height": 200}
                ],
            },
            "parent_asset_id": "asset_parent_123",
        }
        
        response = self.client.post("/image/render", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("artifact_id", data)

if __name__ == '__main__':
    unittest.main()
