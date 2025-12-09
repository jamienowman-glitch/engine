from __future__ import annotations

from engines.security.ingestor import SecurityFeedIngestor


class DummyClient:
    def __init__(self, data):
        self.data = data

    def list_findings(self, *_):
        return self.data


def test_ingest_ghas_normalizes():
    client = DummyClient(
        [{"id": "1", "severity": "high", "location": "file.py:1", "description": "issue", "cwe": "CWE-1"}]
    )
    ingestor = SecurityFeedIngestor(ghas_client=client)
    findings = ingestor.ingest_ghas("t_demo", repo="repo")
    assert findings[0].source == "ghas"
    assert findings[0].severity == "high"


def test_ingest_semgrep_normalizes():
    client = DummyClient([{"id": "2", "severity": "medium", "location": "file.py:2", "message": "msg"}])
    ingestor = SecurityFeedIngestor(semgrep_client=client)
    findings = ingestor.ingest_semgrep("t_demo", repo="repo")
    assert findings[0].source == "semgrep"
    assert findings[0].description == "msg"


def test_ingest_sonar_normalizes():
    client = DummyClient([{"key": "3", "severity": "low", "component": "file.py", "message": "note"}])
    ingestor = SecurityFeedIngestor(sonar_client=client)
    findings = ingestor.ingest_sonar("t_demo", project_key="proj")
    assert findings[0].source == "sonar"
    assert findings[0].location == "file.py"
