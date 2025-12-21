"""Unit tests for the slang normalizer."""
from __future__ import annotations

import copy
import unittest

from engines.bot_better_know.pipeline.slang_normalizer import DEFAULT_LEXICON_PATH, SlangNormalizer, load_lexicon

LEXICON = load_lexicon(DEFAULT_LEXICON_PATH)
NORMALIZER = SlangNormalizer(LEXICON)


def normalize(payload: dict) -> dict:
    data = copy.deepcopy(payload)
    return NORMALIZER.normalize_payload(data)


class SlangNormalizerTest(unittest.TestCase):
    def test_keeps_profanity_intact(self) -> None:
        payload = {
            "segments": [
                {
                    "text": "Fuck that wasteman",
                    "words": [
                        {"text": "Fuck", "start": 0.0, "end": 0.5},
                        {"text": "that", "start": 0.5, "end": 0.7},
                        {"text": "wasteman", "start": 0.7, "end": 1.2},
                    ],
                }
            ]
        }
        result = normalize(payload)
        self.assertEqual(result["segments"][0]["text_norm"], "fuck that wasteman")
        self.assertIn("fuck", result["segments"][0]["text_norm"])

    def test_maps_variants_to_canonical_form(self) -> None:
        payload = {
            "segments": [
                {
                    "text": "Man dem with the ting",
                    "words": [
                        {"text": "Man", "start": 0.0, "end": 0.2},
                        {"text": "dem", "start": 0.2, "end": 0.4},
                        {"text": "with", "start": 0.4, "end": 0.5},
                        {"text": "the", "start": 0.5, "end": 0.6},
                        {"text": "ting", "start": 0.6, "end": 0.8},
                    ],
                }
            ]
        }
        result = normalize(payload)
        segment = result["segments"][0]
        self.assertEqual(segment["text_norm"], "mandem with the ting")
        self.assertTrue(segment["norm_applied"])

    def test_leaves_unknown_tokens_unchanged(self) -> None:
        payload = {
            "segments": [
                {
                    "text": "zzzx",
                    "words": [{"text": "zzzx", "start": 0.0, "end": 0.5}],
                }
            ]
        }
        result = normalize(payload)
        segment = result["segments"][0]
        self.assertEqual(segment["text_raw"], "zzzx")
        self.assertEqual(segment["text_norm"], "zzzx")
        self.assertFalse(segment["norm_applied"])

    def test_word_timing_preserved(self) -> None:
        payload = {
            "segments": [
                {
                    "text": "Bruddah",
                    "words": [{"text": "Bruddah", "start": 1.0, "end": 1.5}],
                }
            ]
        }
        result = normalize(payload)
        word = result["segments"][0]["words"][0]
        self.assertAlmostEqual(word["start"], 1.0)
        self.assertAlmostEqual(word["end"], 1.5)
        self.assertEqual(word["norm"], "brudda")

    def test_text_raw_round_trip(self) -> None:
        payload = {
            "segments": [
                {
                    "text": "Peng gyal in da ends",
                    "words": [{"text": "Peng", "start": 0.0, "end": 0.3}],
                }
            ]
        }
        result = normalize(payload)
        self.assertEqual(result["segments"][0]["text_raw"], "Peng gyal in da ends")


if __name__ == "__main__":
    unittest.main()
