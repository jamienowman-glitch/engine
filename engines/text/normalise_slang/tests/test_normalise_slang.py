from engines.text.normalise_slang.engine import run, NormaliseSlangRequest


def test_normalise_slang_placeholder() -> None:
    data = [{"text": "hello"}]
    resp = run(NormaliseSlangRequest(payloads=data))
    assert resp.normalized == data
