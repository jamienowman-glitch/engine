from __future__ import annotations

from typing import Optional

from engines.feature_flags.models import FeatureFlags
from engines.feature_flags.repository import feature_flag_repo


def get_feature_flags(tenant_id: str, env: str) -> FeatureFlags:
    flags = feature_flag_repo.get_flags(tenant_id, env)
    if flags:
        return flags
    global_flags = feature_flag_repo.get_global_flags(env)
    if global_flags:
        return global_flags.model_copy(update={"tenant_id": tenant_id, "env": env})
    # Default flags if none exist
    return FeatureFlags(tenant_id=tenant_id, env=env)


def update_feature_flags(flags: FeatureFlags) -> FeatureFlags:
    return feature_flag_repo.set_flags(flags)
