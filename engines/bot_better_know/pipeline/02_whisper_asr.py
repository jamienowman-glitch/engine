# app/pipeline/02_whisper_asr.py
"""Run Faster-Whisper with word timestamps (CPU friendly, verbose, resumable)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

from faster_whisper import WhisperModel


def log(msg: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[ASR {now}] {msg}", flush=True)


def transcribe_file(model: WhisperModel, path: Path) -> dict:
    log(f"-> {path.name}  (size={path.stat().st_size/1e6:.1f} MB)")
    segments, info = model.transcribe(
        str(path),
        vad_filter=True,
        word_timestamps=True,
        condition_on_previous_text=False,
        # CPU-friendly knobs:
        beam_size=1,
        best_of=1,
    )
    payload = {
        "file": path.name,
        "language": info.language,
        "duration": float(info.duration),
        "segments": [],
    }
    for seg in segments:
        words = [
            {
                "text": (w.word or "").strip(),
                "start": float(w.start),
                "end": float(w.end),
            }
            for w in (seg.words or [])
        ]
        payload["segments"].append(
            {
                "start": float(seg.start),
                "end": float(seg.end),
                "text": (seg.text or "").strip(),
                "words": words,
            }
        )
    log(f"<- {path.name}  lang={info.language} dur={info.duration:.1f}s")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Whisper ASR (CPU friendly)")
    parser.add_argument("input_dir", help="Directory containing segmented .mp3 files")
    parser.add_argument("output_dir", help="Directory to store JSON payloads")
    args = parser.parse_args()

    src = Path(args.input_dir)
    dst = Path(args.output_dir)
    dst.mkdir(parents=True, exist_ok=True)

    # ENV overrides for convenience
    model_name = os.getenv("WHISPER_MODEL", "medium")      # 'medium' is fast on CPU; use 'large-v3' later
    compute_type = os.getenv("COMPUTE_TYPE", "int8")       # 'int8' works on Mac CPU
    device = os.getenv("DEVICE", "cpu")                    # keep cpu on Mac
    # Threads for CTranslate2 (defaults to all cores if unset)
    ct2_threads = os.getenv("CT2_THREADS")
    if ct2_threads:
        os.environ["CT2_THREADS"] = ct2_threads

    log(f"Loading model={model_name} compute_type={compute_type} device={device} CT2_THREADS={os.getenv('CT2_THREADS','auto')}")
    model = WhisperModel(model_name, compute_type=compute_type, device=device)

    mp3s = sorted(src.glob("*.mp3"))
    if not mp3s:
        log(f"No .mp3 files found in {src}. Did you run 01_segment_ffmpeg.py?")
        sys.exit(1)

    done = 0
    for mp3 in mp3s:
        out_path = dst / f"{mp3.name}.json"
        if out_path.exists():
            log(f"skip {mp3.name} (exists)")
            done += 1
            continue
        try:
            payload = transcribe_file(model, mp3)
            with out_path.open("w", encoding="utf-8") as h:
                json.dump(payload, h, ensure_ascii=False, indent=2)
            done += 1
        except KeyboardInterrupt:
            log("Interrupted by user. Exiting cleanly.")
            sys.exit(130)
        except Exception as e:
            log(f"ERROR {mp3.name}: {e!r}  (continuing)")
            continue

    log(f"Completed {done}/{len(mp3s)} files. Output → {dst}")


if __name__ == "__main__":
    main()
