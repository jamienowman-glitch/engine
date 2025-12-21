"""Simple rule-based flow tagger."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List


def predict_flow(bpm: float, chunk: List[Dict]) -> str:
    avg_syllables = 0.0
    if chunk:
        avg_syllables = sum(bar.get("syllables", 0) for bar in chunk) / len(chunk)
    if 138 <= bpm <= 144:
        mode = "skippy_140"
    elif bpm < 132:
        mode = "half_time"
    else:
        mode = "triplet_machine"

    if avg_syllables < 12:
        mode = "half_time"
    elif avg_syllables > 20 and bpm >= 132:
        mode = "triplet_machine"
    return mode


def annotate_file(path: Path, dst: Path) -> None:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    bars = payload.get("bars", [])
    bpm = float(payload.get("bpm") or 0)

    flow_pairs = []
    for i in range(0, len(bars), 2):
        chunk = bars[i : i + 2]
        if not chunk:
            continue
        flow = predict_flow(bpm, chunk)
        for bar in chunk:
            bar["flow_pred"] = flow
        flow_pairs.append(
            {
                "bar_start": chunk[0]["bar_index"],
                "bar_end": chunk[-1]["bar_index"],
                "flow_pred": flow,
            }
        )

    payload["flow_pairs"] = flow_pairs
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)

    csv_path = dst / path.name.replace(".bars.json", ".flow.csv")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["bar_start", "bar_end", "flow_pred"])
        writer.writeheader()
        writer.writerows(flow_pairs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-tag grime flow classes")
    parser.add_argument("input_dir", help="Directory containing *.bars.json files")
    parser.add_argument("output_dir", help="Directory to store CSV flow tags")
    args = parser.parse_args()

    src = Path(args.input_dir)
    dst = Path(args.output_dir)
    dst.mkdir(parents=True, exist_ok=True)

    for bars_file in sorted(src.glob("*.bars.json")):
        annotate_file(bars_file, dst)


if __name__ == "__main__":
    main()
