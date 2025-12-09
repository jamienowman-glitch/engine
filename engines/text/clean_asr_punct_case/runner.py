"""CLI runner for TEXT.CLEAN.ASR_PUNCT_CASE_V1."""
from __future__ import annotations

import argparse
import json

from engines.text.clean_asr_punct_case.engine import run
from engines.text.clean_asr_punct_case.types import CleanASRPunctCaseInput


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore punctuation/casing for ASR text")
    parser.add_argument("texts", nargs="+", help="ASR text strings")
    args = parser.parse_args()
    res = run(CleanASRPunctCaseInput(texts=args.texts))
    print(json.dumps(res.cleaned_texts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
