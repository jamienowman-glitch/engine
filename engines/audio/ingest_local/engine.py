"""Atomic engine: AUDIO.INGEST.LOCAL_V1

Skeleton entrypoint for local project ingest. Implement real logic in Phase 3.
"""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
from typing import List


@dataclass
class IngestLocalRequest:
    source_dir: Path
    work_dir: Path


@dataclass
class IngestLocalResponse:
    staged_paths: List[Path]


def run(request: IngestLocalRequest) -> IngestLocalResponse:
    """Stage local project assets into working directories.

    Placeholder implementation; replace with real logic.
    """
    # TODO: implement real ingest flow
    request.work_dir.mkdir(parents=True, exist_ok=True)
    return IngestLocalResponse(staged_paths=[])
