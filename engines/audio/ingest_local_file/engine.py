"""Atomic engine: AUDIO.INGEST.LOCAL_FILE_V1."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import List

from engines.audio.ingest_local_file.types import IngestLocalFileInput, IngestLocalFileOutput
from engines.config import runtime_config
from engines.storage.gcs_client import GcsClient


def run(config: IngestLocalFileInput) -> IngestLocalFileOutput:
    """Stage local files into the destination directory."""
    config.dest_dir.mkdir(parents=True, exist_ok=True)
    staged: List[Path] = []
    uploaded: List[str] = []
    raw_bucket = runtime_config.get_raw_bucket()
    gcs = None
    if raw_bucket:
        try:
            gcs = GcsClient()
        except Exception:
            gcs = None
    for src in config.files:
        dst = config.dest_dir / src.name
        shutil.copy2(src, dst)
        staged.append(dst)
        if gcs:
            uploaded.append(gcs.upload_raw_media(config.tenantId, src.name, dst))
    return IngestLocalFileOutput(staged_files=staged, uploaded_urls=uploaded or None)
