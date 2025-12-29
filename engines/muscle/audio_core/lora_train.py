"""Generic LoRA-like training entrypoint.

If torch is available, runs a tiny CPU-safe training loop on dummy data to
produce a mock adapter file. If torch is missing, writes stub metadata and
marks status=unavailable. This keeps the pipeline deterministic and local.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

try:  # optional heavy dep
    import torch
    from torch import nn, optim
except Exception:  # pragma: no cover
    torch = None  # type: ignore
    nn = None  # type: ignore
    optim = None  # type: ignore


def _tiny_train(output_dir: Path) -> Dict[str, str]:
    model = nn.Linear(4, 2)  # type: ignore[arg-type]
    opt = optim.SGD(model.parameters(), lr=0.1)  # type: ignore[attr-defined]
    criterion = nn.MSELoss()  # type: ignore[attr-defined]
    x = torch.randn(8, 4)  # type: ignore[attr-defined]
    y = torch.zeros(8, 2)  # type: ignore[attr-defined]
    for _ in range(5):
        opt.zero_grad()
        loss = criterion(model(x), y)
        loss.backward()
        opt.step()
    adapter_path = output_dir / "adapter.pt"
    torch.save(model.state_dict(), adapter_path)  # type: ignore[attr-defined]
    return {"adapter_path": str(adapter_path)}


def train_lora(config_path: Path) -> Dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as handle:
        cfg = json.load(handle)

    output_dir = Path(cfg.get("output_dir", "outputs/lora"))
    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts: Dict[str, Any] = {
        "base_model": cfg.get("base_model", "meta-llama/Meta-Llama-3-8B-Instruct"),
        "train_path": cfg.get("train_jsonl"),
        "val_path": cfg.get("val_jsonl"),
        "output_dir": str(output_dir),
    }

    if torch is None:
        artifacts.update({"status": "unavailable", "reason": "torch not installed"})
    else:
        adapter_info = _tiny_train(output_dir)
        artifacts.update({"status": "ok", **adapter_info})

    metadata_path = output_dir / "train_metadata.json"
    metadata_path.write_text(json.dumps(artifacts, indent=2), encoding="utf-8")
    artifacts["metadata_path"] = str(metadata_path)
    return artifacts
