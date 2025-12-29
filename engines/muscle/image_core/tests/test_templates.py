"""Tests for template service and HTTP routes."""

import unittest
from unittest.mock import patch

from engines.image_core.template_service import TemplateService, get_template_service
from engines.image_core.template_models import CompositionTemplate, TemplateVariable
from engines.image_core.service import ImageCoreService
from engines.media_v2.service import MediaService, InMemoryMediaRepository, LocalMediaStorage
from fastapi.testclient import TestClient
from fastapi import FastAPI

from engines.image_core.routes import router


class TestTemplateService(unittest.TestCase):
    def setUp(self):
        self.svc = TemplateService()

    def test_save_and_retrieve_template(self):
        """Test saving and retrieving a template."""
        template = CompositionTemplate(
            template_id="test_template_1",
            name="Test Template",
            tenant_id="t_test",
            width=1200,
            height=630,
            background_color="#FFFFFF",
            layers_template=[
                {
                    "name": "header",
                    "color": "$brand_color",
                    "width": 1200,
                    "height": 300,
                }
            ],
            variables=[
                TemplateVariable(
                    name="brand_color",
                    placeholder="$brand_color",
                    type="color",
                    required=True,
                ),
            ],
        )
        
        saved = self.svc.save_template(template)
        self.assertEqual(saved.template_id, template.template_id)
        
        retrieved = self.svc.get_template(template.template_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Test Template")

    def test_list_templates_by_tenant(self):
        """Test listing templates for a specific tenant."""
        template1 = CompositionTemplate(
            template_id="t1",
            name="Template 1",
            tenant_id="t_test",
            width=800,
            height=600,
            layers_template=[],
        )
        template2 = CompositionTemplate(
            template_id="t2",
            name="Template 2",
            tenant_id="t_other",
            width=800,
            height=600,
            layers_template=[],
        )
        
        self.svc.save_template(template1)
        self.svc.save_template(template2)
        
        templates = self.svc.list_templates("t_test")
        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0].template_id, "t1")

    def test_substitute_variables(self):
        """Test variable substitution."""
        text = "Hello $name, your order #$order_id is ready!"
        variables = {"name": "Alice", "order_id": "12345"}
        
        result = self.svc._substitute_variables(text, variables)
        self.assertEqual(result, "Hello Alice, your order #12345 is ready!")

    def test_render_from_template_missing_required_variable(self):
        """Test that missing required variables raise error."""
        template = CompositionTemplate(
            template_id="test_template",
            name="Test",
            tenant_id="t_test",
            width=400,
            height=400,
            layers_template=[{"color": "#FF0000FF", "width": 400, "height": 400}],
            variables=[
                TemplateVariable(name="bg_color", placeholder="$bg_color", type="color", required=True),
            ],
        )
        self.svc.save_template(template)
        
        repo = InMemoryMediaRepository()
        storage = LocalMediaStorage()
        media_svc = MediaService(repo=repo, storage=storage)
        image_svc = ImageCoreService(media_service=media_svc)
        
        with self.assertRaises(ValueError) as ctx:
            self.svc.render_from_template(
                template_id="test_template",
                tenant_id="t_test",
                env="test",
                variables={},  # Missing required variable
                image_service=image_svc,
            )
        self.assertIn("Missing required variables", str(ctx.exception))

    def test_render_from_template_with_valid_variables(self):
        """Test rendering from template with valid variables."""
        template = CompositionTemplate(
            template_id="product_card",
            name="Product Card",
            tenant_id="t_test",
            width=400,
            height=400,
            background_color="#FFFFFF",
            layers_template=[
                {
                    "name": "bg",
                    "color": "$bg_color",
                    "width": 400,
                    "height": 400,
                }
            ],
            variables=[
                TemplateVariable(name="bg_color", placeholder="$bg_color", type="color", required=True),
            ],
        )
        self.svc.save_template(template)
        
        repo = InMemoryMediaRepository()
        storage = LocalMediaStorage()
        media_svc = MediaService(repo=repo, storage=storage)
        image_svc = ImageCoreService(media_service=media_svc)
        
        artifact_id = self.svc.render_from_template(
            template_id="product_card",
            tenant_id="t_test",
            env="test",
            variables={"bg_color": "#FF0000FF"},
            image_service=image_svc,
        )
        
        self.assertIsNotNone(artifact_id)
        artifact = media_svc.get_artifact(artifact_id)
        self.assertIsNotNone(artifact)

    def test_delete_template(self):
        """Test deleting a template."""
        template = CompositionTemplate(
            template_id="to_delete",
            name="Delete Me",
            tenant_id="t_test",
            width=400,
            height=400,
            layers_template=[],
        )
        self.svc.save_template(template)
        
        result = self.svc.delete_template("to_delete")
        self.assertTrue(result)
        
        retrieved = self.svc.get_template("to_delete")
        self.assertIsNone(retrieved)


class TestTemplateRoutes(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
        
        # Real services
        repo = InMemoryMediaRepository()
        storage = LocalMediaStorage()
        media_svc = MediaService(repo=repo, storage=storage)
        self.image_svc = ImageCoreService(media_service=media_svc)
        self.template_svc = TemplateService()
        
        # Patch services
        self.patcher_image = patch(
            'engines.image_core.routes.get_image_core_service',
            return_value=self.image_svc
        )
        self.patcher_template = patch(
            'engines.image_core.routes.get_template_service',
            return_value=self.template_svc
        )
        self.patcher_image.start()
        self.patcher_template.start()

    def tearDown(self):
        self.patcher_image.stop()
        self.patcher_template.stop()

    def test_save_template(self):
        """Test POST /image/templates."""
        payload = {
            "template_id": "instagram_post",
            "name": "Instagram Post",
            "tenant_id": "t_test",
            "width": 1080,
            "height": 1080,
            "background_color": "#FFFFFF",
            "layers_template": [
                {
                    "color": "$bg_color",
                    "width": 1080,
                    "height": 1080,
                }
            ],
            "variables": [
                {
                    "name": "bg_color",
                    "placeholder": "$bg_color",
                    "type": "color",
                    "required": True,
                }
            ],
        }
        
        response = self.client.post("/image/templates", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["template_id"], "instagram_post")

    def test_get_template(self):
        """Test GET /image/templates/{template_id}."""
        template = CompositionTemplate(
            template_id="test_get",
            name="Get Me",
            tenant_id="t_test",
            width=400,
            height=400,
            layers_template=[],
        )
        self.template_svc.save_template(template)
        
        response = self.client.get("/image/templates/test_get")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Get Me")

    def test_get_nonexistent_template(self):
        """Test GET /image/templates/{template_id} with nonexistent template."""
        response = self.client.get("/image/templates/nonexistent")
        self.assertEqual(response.status_code, 404)

    def test_list_templates(self):
        """Test GET /image/templates."""
        template1 = CompositionTemplate(
            template_id="list_test_1",
            name="List Test 1",
            tenant_id="t_test",
            width=400,
            height=400,
            layers_template=[],
        )
        self.template_svc.save_template(template1)
        
        response = self.client.get("/image/templates?tenant_id=t_test")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("templates", data)
        self.assertGreater(len(data["templates"]), 0)

    def test_delete_template(self):
        """Test DELETE /image/templates/{template_id}."""
        template = CompositionTemplate(
            template_id="delete_test",
            name="Delete Test",
            tenant_id="t_test",
            width=400,
            height=400,
            layers_template=[],
        )
        self.template_svc.save_template(template)
        
        response = self.client.delete("/image/templates/delete_test")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "deleted")

    def test_render_from_template(self):
        """Test POST /image/render-from-template."""
        template = CompositionTemplate(
            template_id="render_test",
            name="Render Test",
            tenant_id="t_test",
            width=400,
            height=400,
            background_color="#FFFFFF",
            layers_template=[
                {
                    "color": "$bg_color",
                    "width": 400,
                    "height": 400,
                }
            ],
            variables=[
                TemplateVariable(
                    name="bg_color",
                    placeholder="$bg_color",
                    type="color",
                    required=True,
                ),
            ],
        )
        self.template_svc.save_template(template)
        
        payload = {
            "template_id": "render_test",
            "tenant_id": "t_test",
            "env": "test",
            "variables": {"bg_color": "#00FF00FF"},
        }
        
        response = self.client.post("/image/render-from-template", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("artifact_id", data)


if __name__ == '__main__':
    unittest.main()
