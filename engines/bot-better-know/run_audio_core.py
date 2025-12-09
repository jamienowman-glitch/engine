"""BBK orchestrator using generic audio_core pipeline."""
from __future__ import annotations

import json
from pathlib import Path

from engines.audio_core.runner import run_pipeline


def main(manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text())
    raw_dir = Path(manifest["raw_audio_dir"]).resolve()
    work_dir = Path(manifest["work_dir"]).resolve()
    lora_cfg = Path(manifest["lora_config"]).resolve() if manifest.get("lora_config") else None
    result = run_pipeline(raw_dir, work_dir, lora_cfg)
    out_path = work_dir / "run_result.json"
    out_path.write_text(json.dumps(result, default=str, indent=2), encoding="utf-8")
    print(f"Pipeline complete -> {out_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run BBK pipeline via audio_core")
    parser.add_argument("manifest", type=Path, help="Path to manifest.json")
    args = parser.parse_args()
    main(args.manifest)
