"""Align Whisper words to bars using beat metadata."""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Dict, List

VOWELS = re.compile(r"[aeiouy]+", re.I)


def syllable_count(text: str) -> int:
    words = re.findall(r"[A-Za-z']+", text)
    if not words:
        return 0
    total = 0
    for word in words:
        matches = VOWELS.findall(word)
        total += max(1, len(matches))
    return total


def prefer_norm(path: Path) -> Path:
    base = str(path)
    if base.endswith(".json"):
        norm_path = Path(base[:-5] + ".norm.json")
        if norm_path.exists():
            return norm_path
    return path


def load_meta(aligned_dir: Path, base_name: str) -> Dict:
    meta_path = aligned_dir / base_name.replace(".json", ".meta.json")
    with meta_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def word_norm(word: Dict[str, str]) -> str:
    if word.get("norm"):
        return word["norm"].strip()
    return (word.get("text") or "").lower().strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Align ASR words onto 16-slot bars")
    parser.add_argument("asr_dir", help="Directory containing Whisper JSON payloads")
    parser.add_argument("aligned_dir", help="Directory to write bar JSON files")
    args = parser.parse_args()

    asr_dir = Path(args.asr_dir)
    aligned_dir = Path(args.aligned_dir)
    aligned_dir.mkdir(parents=True, exist_ok=True)

    for json_path in sorted(asr_dir.glob("*.json")):
        if json_path.name.endswith(".norm.json"):
            continue
        payload_path = prefer_norm(json_path)
        with payload_path.open("r", encoding="utf-8") as handle:
            asr = json.load(handle)
        meta = load_meta(aligned_dir, json_path.name)
        bpm = meta.get("bpm", 0)
        downs = meta.get("downbeats") or []
        grid16 = meta.get("grid16", 0.0) or 0.0
        first_downbeat = downs[0] if downs else 0.0
        bar_len = grid16 * 16 if grid16 else 4.0

        bars: Dict[int, List[Dict]] = {}
        for segment in asr.get("segments", []):
            for word in segment.get("words", []) or []:
                start = float(word.get("start", 0.0))
                end = float(word.get("end", start))
                mid = (start + end) / 2.0
                idx = int(math.floor(max(0.0, mid - first_downbeat) / bar_len))
                bars.setdefault(idx, []).append({
                    "raw": (word.get("text") or "").strip(),
                    "norm": word_norm(word),
                    "start": start,
                    "end": end,
                })

        out = {"file": asr.get("file"), "bpm": bpm, "grid16": grid16, "bars": []}
        for idx in sorted(bars.keys()):
            words = bars[idx]
            if not words:
                continue
            raw_line = " ".join(w["raw"] for w in words).strip()
            norm_line = " ".join(w["norm"] for w in words).strip()
            if not raw_line and not norm_line:
                continue
            slots = sorted(
                {
                    int(
                        round(
                            ((w["start"] + w["end"]) / 2.0 - (first_downbeat + idx * bar_len))
                            / grid16
                        )
                    )
                    % 16
                    for w in words
                }
            ) if grid16 else []
            bar_entry = {
                "bar_index": idx + 1,
                "text": raw_line,
                "text_raw": raw_line,
                "text_norm": norm_line,
                "syllables": syllable_count(norm_line or raw_line),
                "stress_slots_16": slots,
            }
            out["bars"].append(bar_entry)

        out_path = aligned_dir / json_path.name.replace(".json", ".bars.json")
        with out_path.open("w", encoding="utf-8") as handle:
            json.dump(out, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
