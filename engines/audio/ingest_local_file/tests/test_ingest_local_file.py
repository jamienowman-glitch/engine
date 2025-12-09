from pathlib import Path

from engines.audio.ingest_local_file.engine import run
from engines.audio.ingest_local_file.types import IngestLocalFileInput


def test_ingest_local_file_copies_files(tmp_path: Path) -> None:
    src = tmp_path / "a.txt"
    src.write_text("hi", encoding="utf-8")
    dest = tmp_path / "dest"
    out = run(IngestLocalFileInput(files=[src], dest_dir=dest))
    assert dest.exists()
    assert len(out.staged_files) == 1
    assert out.staged_files[0].read_text(encoding="utf-8") == "hi"
