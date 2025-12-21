import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from engines.audio_shared.health import (
    DependencyInfo,
    DependencyMissingError,
    MAX_DEPENDENCY_PROBE_TIMEOUT,
    build_backend_health_meta,
    clamp_segment_window,
    check_dependencies,
    prepare_local_asset,
    require_dependency,
)


def _fake_run(cmd, **kwargs):
    return SimpleNamespace(
        returncode=0,
        stdout=f"{cmd[0]} version 1.0.0",
        stderr="",
    )


def test_check_dependencies_all_present():
    with patch("engines.audio_shared.health.shutil.which") as mock_which, \
         patch("engines.audio_shared.health.subprocess.run") as mock_run, \
         patch("engines.audio_shared.health.importlib.import_module") as mock_import:

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_run.side_effect = _fake_run
        mock_import.return_value = SimpleNamespace(__version__="0.9.2")

        deps = check_dependencies()

    assert deps["ffmpeg"].available
    assert deps["ffmpeg"].version.startswith("ffmpeg version")
    assert deps["demucs"].available
    assert deps["librosa"].available
    assert deps["librosa"].version == "0.9.2"


def test_check_dependencies_librosa_missing():
    with patch("engines.audio_shared.health.shutil.which") as mock_which, \
         patch("engines.audio_shared.health.subprocess.run") as mock_run, \
         patch("engines.audio_shared.health.importlib.import_module") as mock_import:

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_run.side_effect = _fake_run
        mock_import.side_effect = ImportError("librosa missing")

        deps = check_dependencies()

    assert deps["librosa"].available is False
    assert "librosa missing" in deps["librosa"].error.lower()


def test_require_dependency_raises():
    with pytest.raises(DependencyMissingError):
        require_dependency("ffmpeg", {"ffmpeg": DependencyInfo(False, None, "not found")})


def test_clamp_segment_window():
    start, end = clamp_segment_window(0, 10)
    assert end - start == 50
    start2, end2 = clamp_segment_window(0, 2000)
    assert end2 - start2 == 1500


def test_prepare_local_asset_requires_gcs():
    with pytest.raises(RuntimeError):
        prepare_local_asset("gs://bucket/file.wav")


def test_prepare_local_asset_local_path():
    path, is_temp = prepare_local_asset("/tmp/existing.wav")
    assert path == "/tmp/existing.wav"
    assert is_temp is False


def test_check_dependencies_timeout():
    with patch("engines.audio_shared.health.shutil.which") as mock_which, \
         patch("engines.audio_shared.health.subprocess.run") as mock_run, \
         patch("engines.audio_shared.health.importlib.import_module") as mock_import:

        mock_which.side_effect = lambda name: f"/usr/bin/{name}"

        def _raise_timeout(*args, **kwargs) -> None:
            raise subprocess.TimeoutExpired(cmd=args[0], timeout=MAX_DEPENDENCY_PROBE_TIMEOUT)

        mock_run.side_effect = _raise_timeout
        mock_import.return_value = SimpleNamespace(__version__="0.9.2")

        deps = check_dependencies()

    assert deps["ffmpeg"].available
    assert deps["ffmpeg"].error
    assert "timed out" in deps["ffmpeg"].error.lower()


def test_build_backend_health_meta_includes_dependencies():
    deps = {
        "librosa": DependencyInfo(True, "0.10.0", None),
        "ffmpeg": DependencyInfo(True, "6.1", None),
    }
    meta = build_backend_health_meta(
        service_name="audio_hits",
        backend_type="librosa",
        primary_dependency="librosa",
        dependencies=deps,
    )

    assert meta["service"] == "audio_hits"
    assert meta["backend_type"] == "librosa"
    assert meta["backend_version"] == "librosa-0.10.0"
    assert "librosa" in meta["dependencies"]
    assert meta["dependencies"]["librosa"]["available"]
