"""CLI runner for AUDIO.INGEST.LOCAL_V1."""
from __future__ import annotations

import argparse
from pathlib import Path

from engines.audio.ingest_local.engine import run
from engines.audio.ingest_local.types import IngestLocalInput


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest local directory into working dir")
    parser.add_argument("source_dir", type=Path, help="Path to source directory")
    parser.add_argument("work_dir", type=Path, help="Path to working directory")
    args = parser.parse_args()
    result = run(IngestLocalInput(source_dir=args.source_dir, work_dir=args.work_dir))
    print(f"Staged {len(result.staged_paths)} file(s) -> {args.work_dir}")


if __name__ == "__main__":
    main()
