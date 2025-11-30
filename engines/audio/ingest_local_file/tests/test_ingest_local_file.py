from pathlib import Path
from engines.audio.ingest_local_file.engine import run, IngestLocalFileRequest


def test_ingest_local_file_placeholder(tmp_path: Path) -> None:
    req = IngestLocalFileRequest(files=[], dest_dir=tmp_path / "dest")
    resp = run(req)
    assert resp.staged_files == []
