from decimal import Decimal

from engines.budget.models import BudgetPolicy
from engines.budget.repository import InMemoryBudgetPolicyRepository


def test_inmemory_policy_saves_and_retrieves_exact():
    repo = InMemoryBudgetPolicyRepository()
    policy = BudgetPolicy(
        tenant_id="t_policy",
        env="dev",
        surface="chat",
        mode="lab",
        app="chat_app",
        threshold=Decimal("5"),
    )
    repo.save_policy(policy)

    retrieved = repo.get_policy(
        tenant_id="t_policy",
        env="dev",
        mode="lab",
        surface="chat",
        app="chat_app",
    )

    assert retrieved is not None
    assert retrieved.threshold == Decimal("5")
    assert retrieved.surface == "chat"


def test_inmemory_policy_falls_back_to_global_surface():
    repo = InMemoryBudgetPolicyRepository()
    policy = BudgetPolicy(
        tenant_id="t_policy",
        env="dev",
        surface=None,
        mode="lab",
        app=None,
        threshold=Decimal("20"),
    )
    repo.save_policy(policy)

    retrieved = repo.get_policy(
        tenant_id="t_policy",
        env="dev",
        mode="lab",
        surface="canvas",
        app="canvas_app",
    )

    assert retrieved is not None
    assert retrieved.surface is None
