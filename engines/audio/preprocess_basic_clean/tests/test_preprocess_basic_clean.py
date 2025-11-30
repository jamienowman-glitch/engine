from pathlib import Path
from engines.audio.preprocess_basic_clean.engine import run, PreprocessBasicCleanRequest


def test_preprocess_basic_clean_placeholder(tmp_path: Path) -> None:
    req = PreprocessBasicCleanRequest(input_paths=[], output_dir=tmp_path / "out")
    resp = run(req)
    assert resp.cleaned_paths == []
