
import unittest
from engines.video_presets.service import _pop_keyframes, _pulse_keyframes, _zoom_in_keyframes, get_preset_service, _built_in_motion_presets

class TestMotionPresets(unittest.TestCase):

    def test_pop_keyframes(self):
        kfs = _pop_keyframes(1000)
        self.assertEqual(len(kfs), 3)
        self.assertEqual(kfs[0].value, 0.0)
        self.assertEqual(kfs[1].value, 1.1)
        self.assertEqual(kfs[2].value, 1.0)
        self.assertEqual(kfs[0].time_ms, 0)
        self.assertEqual(kfs[2].time_ms, 1000)

    def test_pulse_keyframes(self):
        kfs = _pulse_keyframes(1000)
        self.assertEqual(len(kfs), 3)
        self.assertEqual(kfs[0].value, 1.0)
        self.assertEqual(kfs[1].value, 1.1)
        self.assertEqual(kfs[2].value, 1.0)

    def test_zoom_in_keyframes(self):
        kfs = _zoom_in_keyframes(1000)
        self.assertEqual(len(kfs), 2)
        self.assertEqual(kfs[0].value, 1.0)
        self.assertEqual(kfs[1].value, 1.2)

    def test_presets_registered(self):
        presets = _built_in_motion_presets()
        names = [p.name for p in presets]
        self.assertIn("pop_500", names)
        self.assertIn("pop_1000", names)
        self.assertIn("pulse_500", names)
        self.assertIn("zoom_in_1000", names)
        
        # Check details of one
        pop_500 = next(p for p in presets if p.name == "pop_500")
        self.assertIn("pop", pop_500.tags)
        self.assertEqual(pop_500.tracks[0].property, "scale")

if __name__ == "__main__":
    unittest.main()
