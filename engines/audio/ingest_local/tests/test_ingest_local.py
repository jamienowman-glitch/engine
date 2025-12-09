from pathlib import Path

from engines.audio.ingest_local.engine import run
from engines.audio.ingest_local.types import IngestLocalInput


def test_ingest_local_stages_tree(tmp_path: Path) -> None:
    src = tmp_path / "src"
    (src / "nested").mkdir(parents=True)
    (src / "a.txt").write_text("a", encoding="utf-8")
    (src / "nested" / "b.txt").write_text("b", encoding="utf-8")

    work = tmp_path / "work"
    out = run(IngestLocalInput(source_dir=src, work_dir=work))
    assert len(out.staged_paths) == 2
    assert (work / "a.txt").read_text(encoding="utf-8") == "a"
    assert (work / "nested" / "b.txt").read_text(encoding="utf-8") == "b"
