from engines.dataset.events.schemas import DatasetEvent


def test_dataset_event_defaults() -> None:
    ev = DatasetEvent(
        tenantId="t_demo",
        env="dev",
        surface="web",
        agentId="agent1",
        input={"msg": "hi"},
        output={"resp": "ok"},
    )
    assert ev.train_ok is True
    assert ev.pii_flags == {}
    assert ev.utm_source is None
    assert ev.analytics_event_type is None
