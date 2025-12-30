"""Operational status helpers exposed via HTTP and CLI."""
from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import APIRouter

from engines.config import runtime_config

router = APIRouter()


def _build_status_report() -> Dict[str, Any]:
    snapshot = runtime_config.config_snapshot()
    return {
        "storage_provider": snapshot.get("storage_provider"),
        "storage_target": snapshot.get("storage_target"),
        "raw_bucket": snapshot.get("raw_bucket"),
        "datasets_bucket": snapshot.get("datasets_bucket"),
        "memory_backend": snapshot.get("memory_backend"),
        "model_provider": snapshot.get("model_provider"),
        "vector_backend": snapshot.get("vector_backend"),
        "allow_billable_vertex": snapshot.get("allow_billable_vertex"),
        "azure_storage_account": snapshot.get("azure_storage_account"),
        "azure_storage_container": snapshot.get("azure_storage_container"),
        "azure_cosmos_uri": snapshot.get("azure_cosmos_uri"),
        "azure_cosmos_db": snapshot.get("azure_cosmos_db"),
        "azure_cosmos_container": snapshot.get("azure_cosmos_container"),
    }


@router.get("/ops/status")
def status() -> Dict[str, Any]:
    """Reveal storage/memory/model + kill-switch state."""
    return _build_status_report()


def main() -> None:
    print(json.dumps(_build_status_report(), indent=2))


if __name__ == "__main__":
    main()
