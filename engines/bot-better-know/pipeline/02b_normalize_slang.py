"""CLI entry point for slang-preserving ASR normalization."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable

try:  # pragma: no cover - exercised at runtime
    from app.pipeline.slang_normalizer import (
        DEFAULT_LEXICON_PATH,
        SlangNormalizer,
        load_lexicon,
        write_norm_file,
    )
except ImportError:  # script invoked via absolute path inside container
    from slang_normalizer import (  # type: ignore
        DEFAULT_LEXICON_PATH,
        SlangNormalizer,
        load_lexicon,
        write_norm_file,
    )

TRUTHY = {"1", "true", "yes", "on"}


def iter_payloads(src: Path) -> Iterable[Path]:
    for path in src.rglob("*.json"):
        if path.name.endswith(".norm.json"):
            continue
        yield path


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize grime slang transcripts without censorship.")
    parser.add_argument("input_dir", help="Directory containing Whisper JSON payloads")
    parser.add_argument(
        "output_dir",
        help="Destination for normalized payloads (defaults to the same dir)",
    )
    args = parser.parse_args()
    src = Path(args.input_dir).resolve()
    dst = Path(args.output_dir).resolve()
    if not src.exists():
        raise FileNotFoundError(f"Input directory not found: {src}")

    lex_path = os.getenv("SLANG_LEXICON", DEFAULT_LEXICON_PATH)
    normalize_swears = os.getenv("NORMALIZE_SWEARS", "0").lower() in TRUTHY
    entries = load_lexicon(lex_path)
    normalizer = SlangNormalizer(entries, normalize_swears=normalize_swears)

    processed = 0
    for payload_path in iter_payloads(src):
        with payload_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        normalizer.normalize_payload(data)
        write_norm_file(data, payload_path, dst)
        processed += 1

    print(f"normalized {processed} file(s) -> {dst}")


if __name__ == "__main__":
    main()
