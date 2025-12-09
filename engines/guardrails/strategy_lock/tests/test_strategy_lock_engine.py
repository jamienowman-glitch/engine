from engines.guardrails.strategy_lock.engine import run
from engines.guardrails.strategy_lock.schemas import StrategyDecision, StrategyScope


def test_strategy_lock_run_returns_decision() -> None:
    scope = StrategyScope(objective="grow", constraints=["budget"])
    decision = run("t_demo", "dev", "web", {}, scope)
    assert isinstance(decision, StrategyDecision)
    assert "Strategy draft" in decision.draft.summary
