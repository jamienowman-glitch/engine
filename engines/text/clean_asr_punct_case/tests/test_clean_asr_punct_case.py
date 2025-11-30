from engines.text.clean_asr_punct_case.engine import run, CleanASRPunctCaseRequest


def test_clean_asr_punct_case_placeholder() -> None:
    texts = ["hello world"]
    resp = run(CleanASRPunctCaseRequest(texts=texts))
    assert resp.cleaned_texts == texts
