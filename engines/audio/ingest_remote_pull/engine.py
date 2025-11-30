"""Atomic engine: AUDIO.INGEST.REMOTE_PULL_V1"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class IngestRemotePullRequest:
    uris: List[str]
    dest_dir: Path


@dataclass
class IngestRemotePullResponse:
    downloaded: List[Path]


def run(request: IngestRemotePullRequest) -> IngestRemotePullResponse:
    request.dest_dir.mkdir(parents=True, exist_ok=True)
    # TODO: download URIs in Phase 4
    return IngestRemotePullResponse(downloaded=[])
