"""End-to-end orchestrator for the grime pipeline."""
from __future__ import annotations

import os
import subprocess
import sys
import uuid

RUN_ID = os.getenv("RUN_ID", str(uuid.uuid4())[:8])
PROJECT = os.getenv("PROJECT", "aigentfm")
REGION = os.getenv("REGION", "us-central1")
INBOX = os.getenv("INBOX_URI", "gs://aigentfm-inbox/sets")
CORPUS = os.getenv("CORPUS_URI", "gs://aigentfm-corpus")
MODELS = os.getenv("MODELS_URI", "gs://aigentfm-models")


def sh(cmd: str) -> None:
    print(f">> {cmd}")
    rc = subprocess.call(cmd, shell=True)
    if rc != 0:
        sys.exit(rc)


def main() -> None:
    print(f"Starting grime pipeline run_id={RUN_ID} project={PROJECT} region={REGION}")
    sh(f"mkdir -p /tmp/inbox && gsutil -m rsync -r {INBOX} /tmp/inbox")
    sh("mkdir -p /tmp/segments /tmp/asr /tmp/aligned /tmp/datasets /tmp/model")

    sh("python /app/pipeline/01_segment_ffmpeg.py /tmp/inbox /tmp/segments")
    sh("python /app/pipeline/02_whisper_asr.py /tmp/segments /tmp/asr")
    sh("python /app/pipeline/02b_normalize_slang.py /tmp/asr /tmp/asr")
    sh(f"gsutil -m rsync -r /tmp/asr {CORPUS}/asr")

    sh("python /app/pipeline/03_beat_features.py /tmp/segments /tmp/aligned")
    sh("python /app/pipeline/04_align_words.py /tmp/asr /tmp/aligned")
    sh(f"gsutil -m rsync -r /tmp/aligned {CORPUS}/aligned")

    sh("python /app/pipeline/05_auto_tag_flow.py /tmp/aligned /tmp/aligned")
    sh(f"gsutil -m rsync -r /tmp/aligned {CORPUS}/aligned")
    sh(f"gsutil -m rsync -r /tmp/aligned {CORPUS}/tags")

    dsdir = f"/tmp/datasets/{RUN_ID}"
    sh(f"python /app/pipeline/06_pack_jsonl.py /tmp/aligned {dsdir}")
    sh(f"gsutil -m rsync -r {dsdir} {CORPUS}/datasets/{RUN_ID}")

    sh(
        "BASE_MODEL='meta-llama/Meta-Llama-3-8B-Instruct' "
        "python /app/pipeline/07_train_lora.py "
        f"{dsdir}/train.jsonl {dsdir}/val.jsonl /tmp/model"
    )

    sh(f"gsutil -m rsync -r /tmp/model {MODELS}/grime-lora/{RUN_ID}")
    sh(f"gsutil -m rm -r {MODELS}/grime-lora/current || true")
    sh(f"gsutil -m cp -r {MODELS}/grime-lora/{RUN_ID} {MODELS}/grime-lora/current")
    print(f"DONE {RUN_ID}")


if __name__ == "__main__":
    main()
