"""CLI runner for AUDIO.BEAT.FEATURES_V1."""
from __future__ import annotations

import argparse
from pathlib import Path
import json

from engines.audio.beat_features.engine import run
from engines.audio.beat_features.types import BeatFeaturesInput


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze beat/tempo for audio files")
    parser.add_argument("audio_paths", nargs="+", type=Path, help="Audio files")
    args = parser.parse_args()
    res = run(BeatFeaturesInput(audio_paths=args.audio_paths))
    print(json.dumps({str(k): v.dict() for k, v in res.features.items()}, indent=2))


if __name__ == "__main__":
    main()
