from pathlib import Path

import pytest

from engines.text.normalise_slang.engine import run
from engines.text.normalise_slang.types import NormaliseSlangInput


def test_normalise_slang_applies_mapping(tmp_path: Path) -> None:
    lex = tmp_path / "lex.tsv"
    lex.write_text("innit\tin it\n", encoding="utf-8")
    payload = {"segments": [{"text": "Innit bruv"}]}
    out = run(NormaliseSlangInput(payloads=[payload], lexicon_path=lex))
    norm_seg = out.normalized[0]["segments"][0]
    assert norm_seg["text_norm"] == "in it bruv"
    assert norm_seg["norm_applied"] is True


def test_normalise_slang_requires_payloads() -> None:
    with pytest.raises(ValueError):
        NormaliseSlangInput(payloads=[])
