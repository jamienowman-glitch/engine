from pathlib import Path
from engines.audio.ingest_remote_pull.engine import run, IngestRemotePullRequest


def test_ingest_remote_pull_placeholder(tmp_path: Path) -> None:
    req = IngestRemotePullRequest(uris=[], dest_dir=tmp_path / "dest")
    resp = run(req)
    assert resp.downloaded == []
