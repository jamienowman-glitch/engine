"""CLI runner for AUDIO.ASR.WHISPER_V1."""
from __future__ import annotations

import argparse
from pathlib import Path

from engines.audio.asr_whisper.engine import run
from engines.audio.asr_whisper.types import ASRWhisperInput


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Whisper ASR (faster-whisper if installed)")
    parser.add_argument("audio_paths", nargs="+", type=Path, help="Audio files to transcribe")
    parser.add_argument("--model-name", default="medium")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    args = parser.parse_args()
    cfg = ASRWhisperInput(audio_paths=args.audio_paths, model_name=args.model_name, device=args.device, compute_type=args.compute_type)
    out = run(cfg)
    print(out.json())


if __name__ == "__main__":
    main()
