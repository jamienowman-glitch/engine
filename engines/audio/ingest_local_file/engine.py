"""Atomic engine: AUDIO.INGEST.LOCAL_FILE_V1"""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
from typing import List


@dataclass
class IngestLocalFileRequest:
    files: List[Path]
    dest_dir: Path


@dataclass
class IngestLocalFileResponse:
    staged_files: List[Path]


def run(request: IngestLocalFileRequest) -> IngestLocalFileResponse:
    request.dest_dir.mkdir(parents=True, exist_ok=True)
    # TODO: copy/validate files in Phase 4
    return IngestLocalFileResponse(staged_files=[])
