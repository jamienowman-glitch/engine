from engines.dataset.events.schemas import DatasetEvent
from engines.logging.events.engine import run


def test_logging_engine_stub_accepts_event() -> None:
    ev = DatasetEvent(
        tenantId="t_demo",
        env="dev",
        surface="web",
        agentId="agent1",
        input={"msg": "hi"},
        output={"resp": "ok"},
    )
    res = run(ev)
    assert res["status"] == "accepted"
