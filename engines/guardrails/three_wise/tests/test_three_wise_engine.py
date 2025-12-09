from engines.guardrails.three_wise.engine import run
from engines.guardrails.three_wise.schemas import ThreeWiseCheckRequest, ThreeWiseCheckResult


def test_three_wise_run_returns_result() -> None:
    req = ThreeWiseCheckRequest(tenantId="t_demo", env="dev", prompt="hello", surface="web", conversationId="c1")
    res = run(req)
    assert isinstance(res, ThreeWiseCheckResult)
    assert res.aggregate_risk >= 0
