"""Audio core dev runner: preprocess -> beats -> ASR -> dataset -> LoRA (stub)."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from engines.audio.preprocess_basic_clean.engine import run as run_clean
from engines.audio.preprocess_basic_clean.types import PreprocessBasicCleanInput
from engines.audio.beat_features.engine import run as run_beats
from engines.audio.beat_features.types import BeatFeaturesInput
from engines.audio_core import asr_backend, dataset_builder, lora_train


def run_pipeline(raw_dir: Path, work_dir: Path, lora_config: Path | None = None) -> Dict[str, Any]:
    work_dir.mkdir(parents=True, exist_ok=True)
    audio_files = sorted([p for p in raw_dir.iterdir() if p.is_file()])
    clean_out = work_dir / "clean"
    clean_res = run_clean(PreprocessBasicCleanInput(input_paths=audio_files, output_dir=clean_out))

    beats = run_beats(BeatFeaturesInput(audio_paths=clean_res.cleaned_paths))

    asr_results = asr_backend.transcribe_audio(clean_res.cleaned_paths)

    ds_dir = work_dir / "dataset"
    ds_info = dataset_builder.build_dataset(asr_results, ds_dir)

    train_info = None
    if lora_config:
        train_info = lora_train.train_lora(lora_config)

    return {
        "cleaned": clean_res.cleaned_paths,
        "beats": beats.features,
        "asr": asr_results,
        "dataset": ds_info,
        "lora": train_info,
    }
