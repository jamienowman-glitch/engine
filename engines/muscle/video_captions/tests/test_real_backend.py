import unittest
from unittest.mock import MagicMock, patch
import sys

class TestWhisperLocalBackend(unittest.TestCase):
    def setUp(self):
        self.mock_whisper = MagicMock()
        self.mock_whisper.load_model.return_value.transcribe.return_value = {
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello"}
            ]
        }
        
        self.modules_patcher = patch.dict(sys.modules, {'whisper': self.mock_whisper})
        self.modules_patcher.start()
        
        import engines.video_captions.backend
        engines.video_captions.backend.HAS_WHISPER = True
        from engines.video_captions.backend import WhisperLocalBackend
        self.backend_cls = WhisperLocalBackend

    def tearDown(self):
        self.modules_patcher.stop()

    def test_transcribe(self):
        backend = self.backend_cls()
        segments = backend.transcribe("/tmp/fake.wav")
        
        self.mock_whisper.load_model.assert_called_with("tiny")
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["text"], "Hello")

if __name__ == '__main__':
    unittest.main()
