"""SELECTA: slot-based provider/model/secret resolution."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Optional

from engines.common.identity import RequestContext
from engines.common.keys import (
    KeyMaterial,
    MissingKeyConfig,
    TenantKeySelector,
    SLOT_AUTH_JWT_SIGNING,
    SLOT_EMBED_PRIMARY,
    SLOT_LLM_PRIMARY,
    SLOT_METRICS_PRIMARY,
    SLOT_VECTOR_STORE_PRIMARY,
)
from engines.config import runtime_config
from engines.identity.state import identity_repo

# Dev-only env fallbacks per slot
DEV_ENV_VARS: Dict[str, str] = {
    SLOT_LLM_PRIMARY: "OPENAI_API_KEY",
    SLOT_EMBED_PRIMARY: "TEXT_EMBED_MODEL",
    SLOT_VECTOR_STORE_PRIMARY: "VECTOR_ENDPOINT_ID",
    SLOT_METRICS_PRIMARY: "METRICS_ENDPOINT",
    SLOT_AUTH_JWT_SIGNING: "AUTH_JWT_SIGNING",
}


@dataclass
class SelectaResult:
    slot: str
    material: Optional[KeyMaterial]
    metadata: Dict[str, str]


@dataclass
class VectorStoreConfig:
    provider: str
    project: Optional[str]
    region: Optional[str]
    index_id: Optional[str]
    endpoint_id: Optional[str]


@dataclass
class EmbedConfig:
    provider: str
    model_id: Optional[str]


class SelectaResolver:
    def __init__(self, selector: TenantKeySelector) -> None:
        self.selector = selector

    def resolve(self, ctx: RequestContext, slot: str) -> SelectaResult:
        metadata: Dict[str, str] = {}
        material: Optional[KeyMaterial] = None
        canonical_slot = self._canonical_slot(slot)
        try:
            material = self.selector.get_config(ctx.tenant_id, ctx.env, canonical_slot)
            metadata = material.metadata or {}
        except MissingKeyConfig:
            if _is_dev():
                env_val = os.getenv(DEV_ENV_VARS.get(canonical_slot, ""))
                metadata = _dev_metadata(canonical_slot)
                if env_val:
                    material = KeyMaterial(provider="env", secret=env_val, metadata=metadata, config=None)  # type: ignore[arg-type]
            if material is None:
                raise
        return SelectaResult(slot=canonical_slot, material=material, metadata=metadata)

    def vector_store_config(self, ctx: RequestContext) -> VectorStoreConfig:
        res = self.resolve(ctx, SLOT_VECTOR_STORE_PRIMARY)
        meta = res.metadata or {}
        project = meta.get("project") or meta.get("project_id")
        region = meta.get("region")
        index_id = meta.get("index_id")
        endpoint_id = meta.get("endpoint_id")
        if res.material is None and not _is_dev():
            raise MissingKeyConfig(ctx.tenant_id, ctx.env, SLOT_VECTOR_STORE_PRIMARY)
        if res.material is None:  # dev fallback from env vars
            project = project or runtime_config.get_firestore_project()
            region = region or runtime_config.get_env_region_fallback()
            index_id = index_id or os.getenv("VECTOR_INDEX_ID") or os.getenv("VERTEX_VECTOR_INDEX_ID")
            endpoint_id = endpoint_id or os.getenv("VECTOR_ENDPOINT_ID") or os.getenv("VERTEX_VECTOR_ENDPOINT_ID")
        provider = res.material.provider if res.material else "env"
        return VectorStoreConfig(provider=provider, project=project, region=region, index_id=index_id, endpoint_id=endpoint_id)

    def embed_config(self, ctx: RequestContext) -> EmbedConfig:
        res = self.resolve(ctx, SLOT_EMBED_PRIMARY)
        model_id = res.metadata.get("model") or res.metadata.get("model_id")
        if res.material is None and not _is_dev():
            raise MissingKeyConfig(ctx.tenant_id, ctx.env, SLOT_EMBED_PRIMARY)
        if res.material is None:
            model_id = model_id or os.getenv("TEXT_EMBED_MODEL")
        provider = res.material.provider if res.material else "env"
        return EmbedConfig(provider=provider, model_id=model_id)

    @staticmethod
    def _canonical_slot(slot: str) -> str:
        aliases = {
            "vector_primary": SLOT_VECTOR_STORE_PRIMARY,
            "vector_eval": SLOT_VECTOR_STORE_PRIMARY,
            "embed_text": SLOT_EMBED_PRIMARY,
            "embed_image": SLOT_EMBED_PRIMARY,
        }
        return aliases.get(slot, slot)


_default_resolver: Optional[SelectaResolver] = None


def get_selecta_resolver() -> SelectaResolver:
    global _default_resolver
    if _default_resolver is None:
        _default_resolver = SelectaResolver(TenantKeySelector(identity_repo))
    return _default_resolver


def set_selecta_resolver(resolver: SelectaResolver) -> None:
    global _default_resolver
    _default_resolver = resolver


def _dev_metadata(slot: str) -> Dict[str, str]:
    if slot == SLOT_VECTOR_STORE_PRIMARY:
        return {
            "project": runtime_config.get_firestore_project() or "",
            "region": runtime_config.get_env_region_fallback(),
            "index_id": os.getenv("VECTOR_INDEX_ID", ""),
            "endpoint_id": os.getenv("VECTOR_ENDPOINT_ID", ""),
        }
    if slot == SLOT_EMBED_PRIMARY:
        return {"model_id": os.getenv("TEXT_EMBED_MODEL", "")}
    return {}


def _is_dev() -> bool:
    env = (runtime_config.get_env() or "").lower()
    return env in {"dev", "local"}
