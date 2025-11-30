from engines.tag.flow_auto.engine import run, FlowAutoRequest


def test_flow_auto_placeholder() -> None:
    resp = run(FlowAutoRequest(bars=[]))
    assert resp.flow_pairs == []
