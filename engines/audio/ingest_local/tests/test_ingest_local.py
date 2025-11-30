import pytest
from pathlib import Path

from engines.audio.ingest_local.engine import run, IngestLocalRequest


def test_ingest_local_placeholder(tmp_path: Path) -> None:
    req = IngestLocalRequest(source_dir=tmp_path, work_dir=tmp_path / "work")
    resp = run(req)
    assert resp.staged_paths == []
