"""CLI runner for TEXT.NORMALISE.SLANG_V1."""
from __future__ import annotations

import argparse
from pathlib import Path
import json

from engines.text.normalise_slang.engine import run
from engines.text.normalise_slang.types import NormaliseSlangInput


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize slang in ASR payloads")
    parser.add_argument("payloads", nargs="+", type=Path, help="ASR payload JSON files")
    parser.add_argument("--lexicon", type=Path, help="Lexicon TSV path", default=None)
    parser.add_argument("--normalize-swears", action="store_true")
    args = parser.parse_args()
    payload_data = [json.loads(p.read_text()) for p in args.payloads]
    res = run(NormaliseSlangInput(payloads=payload_data, lexicon_path=args.lexicon, normalize_swears=args.normalize_swears))
    for i, payload in enumerate(res.normalized):
        print(f"Payload {i}: norm_applied={any(seg.get('norm_applied') for seg in payload.get('segments', []))}")


if __name__ == "__main__":
    main()
