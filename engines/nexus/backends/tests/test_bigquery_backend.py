from types import SimpleNamespace

from engines.dataset.events.schemas import DatasetEvent
from engines.nexus.backends.bigquery_backend import BigQueryNexusBackend


class _BQClientStub:
    def __init__(self, should_fail: bool = False):
        self.rows = []
        self.should_fail = should_fail

    def insert_rows_json(self, table, rows):
        if self.should_fail:
            raise RuntimeError("stub failure")
        self.rows.extend(rows)
        return []


def test_bigquery_backend_writes_row():
    client = _BQClientStub()
    backend = BigQueryNexusBackend(client=client, dataset="d1", table="t1")
    ev = DatasetEvent(tenantId="t_demo", env="dev", surface="web", agentId="u1", input={}, output={})
    res = backend.write_event(ev)
    assert res["status"] == "accepted"
    assert client.rows
    row = client.rows[0]
    assert row["tenantId"] == "t_demo"
    assert "ingested_at" in row


def test_bigquery_backend_handles_failure():
    client = _BQClientStub(should_fail=True)
    backend = BigQueryNexusBackend(client=client, dataset="d1", table="t1")
    ev = DatasetEvent(tenantId="t_demo", env="dev", surface="web", agentId="u1", input={}, output={})
    res = backend.write_event(ev)
    assert res["status"] == "error"
    assert res["exception"] == "RuntimeError"
