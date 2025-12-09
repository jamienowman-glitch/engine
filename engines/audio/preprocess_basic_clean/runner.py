"""CLI runner for AUDIO.PREPROCESS.BASIC_CLEAN_V1."""
from __future__ import annotations

import argparse
from pathlib import Path

from engines.audio.preprocess_basic_clean.engine import run
from engines.audio.preprocess_basic_clean.types import PreprocessBasicCleanInput


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean audio files with loudnorm + filters")
    parser.add_argument("output_dir", type=Path, help="Output directory for cleaned audio")
    parser.add_argument("input_paths", nargs="+", type=Path, help="Input audio files")
    args = parser.parse_args()
    resp = run(PreprocessBasicCleanInput(input_paths=args.input_paths, output_dir=args.output_dir))
    print(f"Cleaned {len(resp.cleaned_paths)} file(s) -> {args.output_dir}")


if __name__ == "__main__":
    main()
