"""Atomic engine: AUDIO.INGEST.LOCAL_V1."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import List

from engines.audio.ingest_local.types import IngestLocalInput, IngestLocalOutput
from engines.config import runtime_config
from engines.storage.gcs_client import GcsClient


def run(config: IngestLocalInput) -> IngestLocalOutput:
    """Stage all files from source_dir into work_dir."""
    config.work_dir.mkdir(parents=True, exist_ok=True)
    staged: List[Path] = []
    gcs_url_map: List[str] = []
    raw_bucket = runtime_config.get_raw_bucket()
    gcs = None
    if raw_bucket:
        try:
            gcs = GcsClient()
        except Exception:
            gcs = None
    for path in config.source_dir.rglob("*"):
        if path.is_file():
            rel = path.relative_to(config.source_dir)
            dest = config.work_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            staged.append(dest)
            if gcs:
                key = str(rel).replace("\\", "/")
                gcs_url_map.append(gcs.upload_raw_media(config.tenantId, key, dest))
    return IngestLocalOutput(staged_paths=staged, uploaded_urls=gcs_url_map or None)
