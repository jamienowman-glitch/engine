"""CLI runner for AUDIO.INGEST.LOCAL_FILE_V1."""
from __future__ import annotations

import argparse
from pathlib import Path

from engines.audio.ingest_local_file.engine import run
from engines.audio.ingest_local_file.types import IngestLocalFileInput


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage local files into destination directory")
    parser.add_argument("dest_dir", type=Path, help="Destination directory")
    parser.add_argument("files", nargs="+", type=Path, help="Files to stage")
    args = parser.parse_args()
    resp = run(IngestLocalFileInput(files=args.files, dest_dir=args.dest_dir))
    print(f"Staged {len(resp.staged_files)} file(s) -> {args.dest_dir}")


if __name__ == "__main__":
    main()
