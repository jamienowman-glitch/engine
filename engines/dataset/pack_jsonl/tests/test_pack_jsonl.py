from pathlib import Path
from engines.dataset.pack_jsonl.engine import run, PackJsonlRequest


def test_pack_jsonl_placeholder(tmp_path: Path) -> None:
    resp = run(PackJsonlRequest(bars_files=[], output_dir=tmp_path / "out"))
    assert resp.total_samples == 0
    assert resp.train_path is None
    assert resp.val_path is None
