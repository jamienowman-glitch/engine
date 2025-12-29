import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from engines.audio_semantic_timeline.service import WhisperLibrosaBackend, AudioSemanticTimelineSummary

class TestA02Semantics(unittest.TestCase):
    def _librosa_stub(self):
        mod = types.ModuleType("librosa")
        waveform = np.linspace(-0.1, 0.1, 22050)
        mod.load = MagicMock(return_value=(waveform, 22050))
        beat_ns = types.SimpleNamespace(
            beat_track=MagicMock(return_value=(120, [0, 10, 20])),
            frames_to_time=MagicMock(return_value=[0.0, 0.5, 1.0]),
        )
        effects_ns = types.SimpleNamespace(split=lambda y, top_db: [(0, len(y) // 2), (len(y) // 2 + 1, len(y))])
        mod.beat = beat_ns
        mod.effects = effects_ns
        mod.frames_to_time = beat_ns.frames_to_time
        return mod

    def _whisper_stub(self, segments):
        mod = types.ModuleType("whisper")
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"segments": segments}
        mod.load_model = MagicMock(return_value=mock_model)
        return mod

    def test_whisper_integration(self):
        whisper_mod = self._whisper_stub(
            [
                {"start": 0.0, "end": 2.5, "text": "Hello world", "confidence": 0.92},
                {"start": 3.0, "end": 5.0, "text": "Testing audio", "confidence": 0.88},
            ]
        )
        librosa_mod = self._librosa_stub()
        with patch.dict("sys.modules", {"whisper": whisper_mod, "librosa": librosa_mod,
                                        "librosa.beat": librosa_mod.beat, "librosa.effects": librosa_mod.effects}):
            backend = WhisperLibrosaBackend()
            summary = backend.analyze(Path("test.wav"), True, True, 300, 1000)
            speech_events = [e for e in summary.events if e.kind == "speech"]
            self.assertGreaterEqual(len(speech_events), 2)
            self.assertEqual(speech_events[0].transcription, "Hello world")
            self.assertEqual(speech_events[0].start_ms, 0)
            self.assertEqual(speech_events[0].end_ms, 2500)
            self.assertIsNotNone(speech_events[0].loudness_lufs)

    def test_librosa_integration(self):
        librosa_mod = self._librosa_stub()
        with patch.dict("sys.modules", {"librosa": librosa_mod,
                                        "librosa.beat": librosa_mod.beat, "librosa.effects": librosa_mod.effects}):
            backend = WhisperLibrosaBackend()
            summary = backend.analyze(Path("test.wav"), True, False, 300, 1000)
            self.assertTrue(len(summary.beats) >= 3)
            times = [beat.time_ms for beat in summary.beats]
            self.assertEqual(sorted(times), times)
            self.assertFalse(summary.events)

    def test_fallback_wrapper(self):
        with patch("engines.audio_semantic_timeline.service._try_import", return_value=None):
            backend = WhisperLibrosaBackend()
            summary = backend.analyze(Path("test.wav"), True, True, 300, 1000)
            self.assertTrue(len(summary.events) > 0)
            self.assertIsNone(summary.events[0].transcription)

if __name__ == '__main__':
    unittest.main()
