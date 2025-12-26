
import unittest
from engines.video_presets.service import VideoTemplate, PresetService, InMemoryPresetRepository, get_preset_service, set_preset_service

class TestSocialTemplates(unittest.TestCase):
    def setUp(self):
        self.service = PresetService(repo=InMemoryPresetRepository())
        set_preset_service(self.service)

    def test_built_in_templates_exist(self):
        templates = self.service.list_templates(tenant_id="any", env="dev")
        names = [t.name for t in templates]
        self.assertIn("vlog_4_3", names)
        self.assertIn("social_square_punchy", names)
        
        # Verify vlog_4_3 details
        vlog = next(t for t in templates if t.name == "vlog_4_3")
        self.assertEqual(vlog.render_profile, "social_4_3_h264")
        self.assertEqual(vlog.filter_preset_id, "style_vlog")
        self.assertEqual(vlog.motion_preset_id, "shake_1")

    def test_create_and_get_template(self):
        tmpl = VideoTemplate(
            tenant_id="t1",
            env="dev",
            name="custom_template",
            description="My Custom Template",
            render_profile="social_1080p_h264",
            filter_preset_id="style_cinematic",
            tags=["custom"]
        )
        created = self.service.create_template(tmpl)
        self.assertEqual(created.name, "custom_template")
        
        fetched = self.service.get_template(created.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "custom_template")

    def test_list_templates_filtering(self):
        self.service.create_template(VideoTemplate(
            tenant_id="t1", env="dev", name="t1_temp", render_profile="p1", tags=["cool"]
        ))
        self.service.create_template(VideoTemplate(
            tenant_id="t2", env="dev", name="t2_temp", render_profile="p1", tags=["cool"]
        ))
        
        # Tenant filter
        t1_list = self.service.list_templates(tenant_id="t1", env="dev")
        # should include built-ins (global env) + t1
        # built-ins have tenant_id="built_in". Logic in list_templates:
        # built_ins = [t for t in self._built_in_templates if ...]
        # user_templates = self.repo.list_templates(tenant_id...)
        # returns built_ins + user_templates.
        
        names = [t.name for t in t1_list]
        self.assertIn("t1_temp", names)
        self.assertNotIn("t2_temp", names)
        self.assertIn("vlog_4_3", names) # Built-in

if __name__ == "__main__":
    unittest.main()
