"""Atomic engine: AUDIO.INGEST.REMOTE_PULL_V1."""
from __future__ import annotations

import shutil
import urllib.request
from pathlib import Path
from typing import List

from engines.audio.ingest_remote_pull.types import IngestRemotePullInput, IngestRemotePullOutput
from engines.config import runtime_config
from engines.storage.gcs_client import GcsClient


def _download(uri: str, dest: Path) -> None:
    with urllib.request.urlopen(uri) as response, dest.open("wb") as out:  # nosec B310
        shutil.copyfileobj(response, out)


def run(config: IngestRemotePullInput) -> IngestRemotePullOutput:
    """Fetch remote resources into dest_dir."""
    config.dest_dir.mkdir(parents=True, exist_ok=True)
    downloaded: List[Path] = []
    uploaded: List[str] = []
    raw_bucket = runtime_config.get_raw_bucket()
    gcs = None
    if raw_bucket:
        try:
            gcs = GcsClient()
        except Exception:
            gcs = None
    for uri in config.uris:
        filename = Path(uri).name or "downloaded"
        dest_path = config.dest_dir / filename
        _download(uri, dest_path)
        downloaded.append(dest_path)
        if gcs:
            uploaded.append(gcs.upload_raw_media(config.tenantId, filename, dest_path))
    return IngestRemotePullOutput(downloaded=downloaded, uploaded_urls=uploaded or None)
