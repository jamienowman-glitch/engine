"""Dev runtime settings helper for northstar-os-dev (PLAN-026)."""
from __future__ import annotations

from dataclasses import dataclass

from engines.config import runtime_config


@dataclass
class Settings:
    tenant_id: str | None
    raw_bucket: str | None
    datasets_bucket: str | None
    nexus_backend: str | None
    project_id: str | None
    region: str | None


def get_settings() -> Settings:
    cfg = runtime_config.config_snapshot()
    return Settings(
        tenant_id=cfg["tenant_id"],
        raw_bucket=cfg["raw_bucket"],
        datasets_bucket=cfg["datasets_bucket"],
        nexus_backend=cfg["nexus_backend"],
        project_id=cfg["gcp_project"],
        region=cfg["region"],
    )
