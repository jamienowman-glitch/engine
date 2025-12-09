from pathlib import Path
from io import BytesIO

import pytest

from engines.audio.ingest_remote_pull import engine
from engines.audio.ingest_remote_pull.types import IngestRemotePullInput


def test_ingest_remote_pull_downloads(monkeypatch, tmp_path: Path) -> None:
    content = b"hello"

    class DummyResponse(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self.close()

    def fake_urlopen(url):  # type: ignore[no-untyped-def]
        return DummyResponse(content)

    monkeypatch.setattr(engine.urllib.request, "urlopen", fake_urlopen)

    cfg = IngestRemotePullInput(uris=["http://example.com/a.mp3"], dest_dir=tmp_path / "dest")
    out = engine.run(cfg)
    assert len(out.downloaded) == 1
    assert out.downloaded[0].read_bytes() == content


def test_ingest_remote_pull_requires_uris() -> None:
    with pytest.raises(ValueError):
        IngestRemotePullInput(uris=[], dest_dir=Path("/tmp/x"))
