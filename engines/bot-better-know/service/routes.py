"""FastAPI routes for BBK local pipeline + training."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from engines.audio_core import lora_train
from engines.audio_core import runner as audio_core_runner

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "bbk"}


def _run_id() -> str:
    return f"bbk-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"


def _save_upload(file: UploadFile, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / file.filename
    with dest_path.open("wb") as handle:
        handle.write(file.file.read())
    return dest_path


def _write_run_result(run_dir: Path, payload: dict) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "run_result.json"
    out_path.write_text(json.dumps(payload, default=str, indent=2), encoding="utf-8")
    return out_path


def _default_paths() -> dict:
    root = Path("engines/bot-better-know")
    return {
        "uploads": root / "data/uploads",
        "runs": root / "data/runs",
        "datasets": root / "data/work_local/dataset",
        "models": root / "data/model",
    }


@router.post("/bbk/upload-and-process")
def upload_and_process(file: UploadFile = File(...)) -> dict:
    paths = _default_paths()
    run_id = _run_id()
    upload_path = _save_upload(file, paths["uploads"])

    # Run audio_core pipeline using a run-specific work_dir
    run_dir = paths["runs"] / run_id
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest_file = raw_dir / upload_path.name
    dest_file.write_bytes(upload_path.read_bytes())

    result = audio_core_runner.run_pipeline(raw_dir=raw_dir, work_dir=run_dir, lora_config=None)
    result_payload = {
        "runId": run_id,
        "status": "accepted",
        "uploaded": str(upload_path),
        "work_dir": str(run_dir),
        "asr_status": result.get("asr", [{}])[0].get("status") if result.get("asr") else None,
        "notes": "audio_core pipeline kicked off",
    }
    _write_run_result(run_dir, result_payload)
    return result_payload


@router.post("/bbk/start-training")
def start_training(runId: str | None = None) -> dict:
    paths = _default_paths()
    if runId:
        dataset_dir = paths["runs"] / runId / "dataset"
        model_dir = paths["models"] / runId
    else:
        dataset_dir = paths["datasets"]
        model_dir = paths["models"] / "latest"

    train_path = dataset_dir / "train.jsonl"
    val_path = dataset_dir / "val.jsonl"
    if not train_path.exists() or not val_path.exists():
        return {"status": "error", "reason": "no_dataset"}

    cfg = {
        "base_model": "meta-llama/Meta-Llama-3-8B-Instruct",
        "train_jsonl": str(train_path),
        "val_jsonl": str(val_path),
        "output_dir": str(model_dir),
    }
    cfg_path = model_dir / "lora_config.json"
    model_dir.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    train_info = lora_train.train_lora(cfg_path)
    return {
        "status": "accepted",
        "mode": "local_cpu",
        "train_info": train_info,
        "note": "LoRA training started; check model dir for artifacts",
    }
