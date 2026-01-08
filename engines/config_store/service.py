from __future__ import annotations

from typing import Dict, Any, Optional

from pydantic import BaseModel

from engines.common.error_envelope import error_response
from engines.common.identity import RequestContext
from engines.config_store.repository import ConfigStoreRepository, ConfigRecord

TOOL_CANVAS_MODE_KEY = "tool_canvas_mode"
TOOL_CANVAS_MODE_VALUES = {"A", "B"}


class ConfigPayload(BaseModel):
    version: int
    values: Dict[str, Any]


class EffectiveConfigPayload(BaseModel):
    """Overlay of system → tenant → surface config versions and values."""

    version: int
    values: Dict[str, Any]
    sources: Dict[str, int]


class ConfigService:
    def __init__(self, repo: Optional[ConfigStoreRepository] = None) -> None:
        self.repo = repo or ConfigStoreRepository()

    def validate_values(self, values: Dict[str, Any]) -> None:
        mode = values.get(TOOL_CANVAS_MODE_KEY)
        if mode is not None and mode not in TOOL_CANVAS_MODE_VALUES:
            error_response(
                code="config.invalid_tool_canvas_mode",
                message=f"tool_canvas_mode must be one of {sorted(TOOL_CANVAS_MODE_VALUES)}",
                status_code=400,
                resource_kind="config_store",
            )

    def get_config(self, ctx: RequestContext, scope: str, identifier: str) -> ConfigPayload:
        record = self.repo.get(ctx, scope, identifier)
        if not record:
            return ConfigPayload(version=0, values={})
        return ConfigPayload(version=record.version, values=record.values.copy())

    def save_config(self, ctx: RequestContext, scope: str, identifier: str, version: int, values: Dict[str, Any]) -> ConfigPayload:
        self.validate_values(values)
        record = self.repo.save(ctx, scope, identifier, version, values)
        return ConfigPayload(version=record.version, values=record.values.copy())

    def get_effective_config(self, ctx: RequestContext) -> EffectiveConfigPayload:
        """Merge system → tenant → surface configuration with deterministic precedence."""
        sources = {"system": 0, "tenant": 0, "surface": 0}
        merged_values: Dict[str, Any] = {}
        highest_version = 0

        for scope, identifier in [
            ("system", "system"),
            ("tenant", ctx.tenant_id),
        ] + ([("surface", ctx.surface_id)] if ctx.surface_id else []):
            payload = self.get_config(ctx, scope, identifier)
            sources[scope] = payload.version
            highest_version = max(highest_version, payload.version)
            merged_values.update(payload.values)

        # Validate the final overlay so clients never see invalid modes.
        self.validate_values(merged_values)

        return EffectiveConfigPayload(
            version=highest_version,
            values=merged_values,
            sources=sources,
        )


_default_service: Optional[ConfigService] = None


def get_config_service() -> ConfigService:
    global _default_service
    if _default_service is None:
        _default_service = ConfigService()
    return _default_service


def set_config_service(service: ConfigService) -> None:
    global _default_service
    _default_service = service
