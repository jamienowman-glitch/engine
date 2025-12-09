"""CLI runner for TAG.FLOW.AUTO_V1."""
from __future__ import annotations

import argparse
import json

from engines.tag.flow_auto.engine import run
from engines.tag.flow_auto.types import FlowAutoInput


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-tag flow for bars")
    parser.add_argument("bars_json", type=str, help="Path to bars JSON file")
    args = parser.parse_args()
    bars = json.loads(open(args.bars_json, "r", encoding="utf-8").read())
    res = run(FlowAutoInput(bars=bars))
    print(json.dumps({"flow_pairs": [fp.dict() for fp in res.flow_pairs]}, indent=2))


if __name__ == "__main__":
    main()
