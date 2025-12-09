import pytest

from engines.text.clean_asr_punct_case.engine import run
from engines.text.clean_asr_punct_case.types import CleanASRPunctCaseInput


def test_clean_asr_punct_case_sentence_case() -> None:
    out = run(CleanASRPunctCaseInput(texts=["hello world"]))
    assert out.cleaned_texts[0].startswith("Hello")
    assert out.cleaned_texts[0].endswith(".")


def test_clean_asr_requires_texts() -> None:
    with pytest.raises(ValueError):
        CleanASRPunctCaseInput(texts=[])
