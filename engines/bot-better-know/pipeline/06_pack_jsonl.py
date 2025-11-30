"""Pack aligned bars into instruction-style JSONL datasets."""
from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

RHYME_RE = re.compile(r"[aeiouy]+[^aeiouy]*$", re.I)


def rough_rhyme(text: str) -> str:
    words = re.findall(r"[A-Za-z']+", (text or "").lower())
    if not words:
        return ""
    match = RHYME_RE.search(words[-1])
    if match:
        return match.group(0)
    return words[-1][-2:]


def fallback_flow(bpm: float) -> str:
    if 138 <= bpm <= 144:
        return "skippy_140"
    if bpm < 132:
        return "half_time"
    return "triplet_machine"


def load_flow_pairs(payload: Dict, csv_path: Path) -> Dict[Tuple[int, int], str]:
    pairs = {}
    for pair in payload.get("flow_pairs", []) or []:
        key = (int(pair["bar_start"]), int(pair["bar_end"]))
        pairs[key] = pair["flow_pred"]
    if pairs:
        return pairs
    if csv_path.exists():
        import csv

        with csv_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                key = (int(row["bar_start"]), int(row["bar_end"]))
                pairs[key] = row["flow_pred"]
    return pairs


def bar_texts(bar: Dict) -> Tuple[str, str]:
    raw = (bar.get("text_raw") or bar.get("text") or "").strip()
    norm = (bar.get("text_norm") or raw.lower()).strip()
    return raw, norm


def pack_file(path: Path) -> List[Dict]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    bars = payload.get("bars", [])
    bpm = float(payload.get("bpm") or 0)
    flow_pairs = load_flow_pairs(payload, path.with_suffix(".flow.csv"))
    samples = []
    for i in range(0, len(bars) - 1, 2):
        a, b = bars[i], bars[i + 1]
        bar_start = int(a.get("bar_index", i + 1))
        bar_end = int(b.get("bar_index", i + 2))
        flow = flow_pairs.get((bar_start, bar_end), fallback_flow(bpm))
        raw_a, norm_a = bar_texts(a)
        raw_b, norm_b = bar_texts(b)
        density = "high" if flow != "half_time" else "low"
        sample = {
            "system": "You are a grime bars writer. Output JSON with exactly 2 bars.",
            "input": {
                "bpm": bpm,
                "flow": flow,
                "rhyme_scheme": random.choice(["AABB", "ABAB"]),
                "density": density,
                "kick_slots": [0, 4, 8, 12],
                "snare_slots": [4, 12],
                "topic": "East London night",
                "local": ["Hackney"],
                "reload_cue_at": [8, 16],
                "n_bars": 2,
            },
            "output": {
                "flow": flow,
                "bpm": bpm,
                "bars": [
                    {
                        "text": raw_a,
                        "text_raw": raw_a,
                        "text_norm": norm_a,
                        "syllables": a.get("syllables", 0),
                        "end_rhyme": rough_rhyme(norm_a),
                        "multis": [],
                        "stress_slots_16": a.get("stress_slots_16", []),
                    },
                    {
                        "text": raw_b,
                        "text_raw": raw_b,
                        "text_norm": norm_b,
                        "syllables": b.get("syllables", 0),
                        "end_rhyme": rough_rhyme(norm_b),
                        "multis": [],
                        "stress_slots_16": b.get("stress_slots_16", []),
                    },
                ],
                "reload_cue_at": [8, 16],
            },
        }
        samples.append(sample)
    return samples


def main() -> None:
    parser = argparse.ArgumentParser(description="Pack training/validation JSONL files")
    parser.add_argument("aligned_dir", help="Directory containing *.bars.json files")
    parser.add_argument("output_dir", help="Output directory for train/val splits")
    args = parser.parse_args()

    aligned_dir = Path(args.aligned_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_samples: List[Dict] = []
    for bars_file in sorted(aligned_dir.glob("*.bars.json")):
        all_samples.extend(pack_file(bars_file))

    random.shuffle(all_samples)
    val_size = max(1, int(0.1 * len(all_samples))) if all_samples else 0
    train_samples = all_samples[val_size:]
    val_samples = all_samples[:val_size]

    (out_dir / "train.jsonl").write_text(
        "\n".join(json.dumps(obj, ensure_ascii=False) for obj in train_samples),
        encoding="utf-8",
    )
    (out_dir / "val.jsonl").write_text(
        "\n".join(json.dumps(obj, ensure_ascii=False) for obj in val_samples),
        encoding="utf-8",
    )
    print(f"pairs {len(all_samples)}")


if __name__ == "__main__":
    main()
