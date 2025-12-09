"""CLI runner for ALIGN.AUDIO_TEXT.BARS_V1."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engines.align.audio_text_bars.engine import run
from engines.align.audio_text_bars.types import AlignAudioTextBarsInput


def main() -> None:
    parser = argparse.ArgumentParser(description="Align ASR words to bars")
    parser.add_argument("asr_payloads", nargs="+", type=Path, help="ASR payload JSON files")
    parser.add_argument("--beat-meta", type=Path, help="Beat metadata JSON", default=None)
    args = parser.parse_args()
    payloads = [json.loads(p.read_text()) for p in args.asr_payloads]
    beat_meta = json.loads(args.beat_meta.read_text()) if args.beat_meta else {}
    res = run(AlignAudioTextBarsInput(asr_payloads=payloads, beat_metadata=beat_meta))
    print(json.dumps([b.dict() for b in res.bars], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
