from pathlib import Path

import pytest

from engines.audio import preprocess_basic_clean as mod
from engines.audio.preprocess_basic_clean.engine import run
from engines.audio.preprocess_basic_clean.types import PreprocessBasicCleanInput


def test_preprocess_basic_clean_invokes_ffmpeg(monkeypatch, tmp_path: Path) -> None:
    src = tmp_path / "a.wav"
    src.write_bytes(b"audio")
    out_dir = tmp_path / "out"

    calls = []

    def fake_check_call(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        (out_dir / "a_clean.wav").write_bytes(b"clean")

    monkeypatch.setattr(mod, "subprocess", type("S", (), {"check_call": fake_check_call}))
    monkeypatch.setattr(mod.shutil, "which", lambda name: "ffmpeg")

    res = run(PreprocessBasicCleanInput(input_paths=[src], output_dir=out_dir))
    assert len(res.cleaned_paths) == 1
    assert res.cleaned_paths[0].name == "a_clean.wav"
    assert calls, "ffmpeg should be invoked"


def test_preprocess_basic_clean_requires_ffmpeg(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError):
        run(PreprocessBasicCleanInput(input_paths=[tmp_path], output_dir=tmp_path / "o"))
