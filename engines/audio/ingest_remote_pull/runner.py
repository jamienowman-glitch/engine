"""CLI runner for AUDIO.INGEST.REMOTE_PULL_V1."""
from __future__ import annotations

import argparse
from pathlib import Path

from engines.audio.ingest_remote_pull.engine import run
from engines.audio.ingest_remote_pull.types import IngestRemotePullInput


def main() -> None:
    parser = argparse.ArgumentParser(description="Download remote URIs to dest_dir")
    parser.add_argument("dest_dir", type=Path, help="Destination directory")
    parser.add_argument("uris", nargs="+", help="Remote URIs")
    args = parser.parse_args()
    resp = run(IngestRemotePullInput(uris=args.uris, dest_dir=args.dest_dir))
    print(f"Downloaded {len(resp.downloaded)} file(s) -> {args.dest_dir}")


if __name__ == "__main__":
    main()
