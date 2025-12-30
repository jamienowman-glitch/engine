"""Runtime configuration helpers for engines."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Dict, Optional

from engines.common.identity import RequestContext
from engines.cost.vertex_guard import allow_billable_vertex

SLOT_VECTOR_STORE_PRIMARY = "vector_store_primary"
SLOT_EMBED_PRIMARY = "embed_primary"

def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(name, default)


def _default_project_id() -> str:
    """Fallback project identifier for non-request contexts."""
    return _get_env("PROJECT_ID") or _get_env("GCP_PROJECT") or "runtime_config"


def get_tenant_id() -> Optional[str]:
    return _get_env("TENANT_ID")


def get_env() -> Optional[str]:
    return _get_env("ENV") or _get_env("APP_ENV")


def get_env_region_fallback() -> str:
    return _get_env("GCP_REGION") or _get_env("REGION") or "us-central1"


def _is_dev_env() -> bool:
    env = (get_env() or "dev").lower()
    return env in {"dev", "local"}


def _selecta_metadata(slot: str, ctx: Optional[RequestContext] = None) -> Dict[str, str]:
    """Resolve metadata for a slot via SELECTA; dev falls back to empty metadata."""
    from engines.common.keys import MissingKeyConfig  # local import to avoid circular
    from engines.common.selecta import get_selecta_resolver

    try:
        try:
            context = ctx or RequestContext(
                request_id="runtime_config",
                tenant_id=get_tenant_id() or "t_dev",
                env=get_env() or "dev",
                project_id=_default_project_id(),
            )
        except Exception:
            context = RequestContext(
                request_id="runtime_config",
                tenant_id="t_dev",
                env="dev",
                project_id=_default_project_id(),
            )
        result = get_selecta_resolver().resolve(context, slot)
        return result.metadata or {}
    except MissingKeyConfig:
        # In dev/local we allow env-var escape hatches; prod must set slots.
        if _is_dev_env():
            return {}
        raise
    except Exception:
        return {}


def get_nexus_backend() -> Optional[str]:
    return (_get_env("NEXUS_BACKEND") or "").lower() or None


def get_nexus_bq_dataset() -> Optional[str]:
    return _get_env("NEXUS_BQ_DATASET")


def get_nexus_bq_table() -> Optional[str]:
    return _get_env("NEXUS_BQ_TABLE")


def get_raw_bucket() -> Optional[str]:
    return _get_env("RAW_BUCKET")


def get_datasets_bucket() -> Optional[str]:
    return _get_env("DATASETS_BUCKET")


def get_firestore_project() -> Optional[str]:
    return _get_env("GCP_PROJECT_ID") or _get_env("GCP_PROJECT")


def get_region() -> Optional[str]:
    meta = _selecta_metadata(SLOT_VECTOR_STORE_PRIMARY)
    value = meta.get("region") if meta else None
    return value or get_env_region_fallback()


def get_vector_index_id() -> Optional[str]:
    meta = _selecta_metadata(SLOT_VECTOR_STORE_PRIMARY)
    value = meta.get("index_id") if meta else None
    return value or _get_env("VECTOR_INDEX_ID") or _get_env("VERTEX_VECTOR_INDEX_ID")


def get_vector_endpoint_id() -> Optional[str]:
    meta = _selecta_metadata(SLOT_VECTOR_STORE_PRIMARY)
    value = meta.get("endpoint_id") if meta else None
    return value or _get_env("VECTOR_ENDPOINT_ID") or _get_env("VERTEX_VECTOR_ENDPOINT_ID")


def get_text_embedding_model_id() -> Optional[str]:
    meta = _selecta_metadata(SLOT_EMBED_PRIMARY)
    value = (meta.get("model_id") or meta.get("model")) if meta else None
    return value or _get_env("TEXT_EMBED_MODEL") or _get_env("VERTEX_TEXT_EMBED_MODEL")


def get_image_embedding_model_id() -> Optional[str]:
    meta = _selecta_metadata(SLOT_EMBED_PRIMARY)
    value = (meta.get("image_model_id") or meta.get("model_id")) if meta else None
    return value or _get_env("IMAGE_EMBED_MODEL") or _get_env("VERTEX_IMAGE_EMBED_MODEL")


def get_vector_project() -> Optional[str]:
    meta = _selecta_metadata(SLOT_VECTOR_STORE_PRIMARY)
    value = meta.get("project") if meta else None
    return value or _get_env("VECTOR_PROJECT_ID") or get_firestore_project()


def get_vertex_eval_model_id() -> Optional[str]:
    return _get_env("VERTEX_EVAL_MODEL_ID")


def get_bedrock_eval_model_id() -> Optional[str]:
    return _get_env("BEDROCK_EVAL_MODEL_ID")


def get_ragas_eval_url() -> Optional[str]:
    return _get_env("RAGAS_EVAL_URL")


def get_ragas_eval_token() -> Optional[str]:
    return _get_env("RAGAS_EVAL_TOKEN")


def get_vertex_forecast_dataset() -> Optional[str]:
    return _get_env("VERTEX_FORECAST_DATASET")


def get_vertex_forecast_table() -> Optional[str]:
    return _get_env("VERTEX_FORECAST_TABLE")


def get_bq_ml_dataset() -> Optional[str]:
    return _get_env("BQ_ML_FORECAST_DATASET")


def get_bq_ml_table() -> Optional[str]:
    return _get_env("BQ_ML_FORECAST_TABLE")


def get_aws_forecast_role_arn() -> Optional[str]:
    return _get_env("AWS_FORECAST_ROLE_ARN")


def get_aws_forecast_dataset_group() -> Optional[str]:
    return _get_env("AWS_FORECAST_DATASET_GROUP")


def get_ghas_app_id() -> Optional[str]:
    return _get_env("GHAS_APP_ID")


def get_ghas_private_key_secret() -> Optional[str]:
    return _get_env("GHAS_PRIVATE_KEY_SECRET")


def get_dependabot_token_secret() -> Optional[str]:
    return _get_env("DEPENDABOT_TOKEN_SECRET")


def get_semgrep_token_secret() -> Optional[str]:
    return _get_env("SEMGREP_TOKEN_SECRET")


def get_sonar_token_secret() -> Optional[str]:
    return _get_env("SONAR_TOKEN_SECRET")


def get_imagen_api_key_secret() -> Optional[str]:
    return _get_env("IMAGEN_API_KEY_SECRET")


def get_nova_api_key_secret() -> Optional[str]:
    return _get_env("NOVA_API_KEY_SECRET")


def get_braket_role_arn() -> Optional[str]:
    return _get_env("BRAKET_ROLE_ARN")


def get_braket_region() -> Optional[str]:
    return _get_env("BRAKET_REGION")




def get_memory_backend() -> Optional[str]:
    return _get_env("MEMORY_BACKEND")


def get_storage_target() -> Optional[str]:
    return get_raw_bucket() or get_datasets_bucket()


def get_storage_provider() -> str:
    if get_azure_storage_account() and get_azure_storage_container():
        return "azure_blob"
    raw_bucket = (get_raw_bucket() or "").strip()
    if raw_bucket.lower().startswith("gs://"):
        return "gcs"
    if raw_bucket.lower().startswith("s3://"):
        return "s3"
    datasets_bucket = get_datasets_bucket() or ""
    if datasets_bucket.lower().startswith("gs://"):
        return "gcs"
    if raw_bucket or datasets_bucket:
        return "s3"
    return "unknown"


def get_model_provider() -> Optional[str]:
    for name in ("MODEL_PROVIDER", "LLM_PROVIDER"):
        value = _get_env(name)
        if value:
            return value
    if _get_env("VERTEX_MODEL"):
        return "vertex"
    return None


def get_azure_storage_account() -> Optional[str]:
    return _get_env("AZURE_STORAGE_ACCOUNT")


def get_azure_storage_container() -> Optional[str]:
    return _get_env("AZURE_STORAGE_CONTAINER")


def get_azure_storage_key() -> Optional[str]:
    return _get_env("AZURE_STORAGE_KEY")


def get_azure_cosmos_uri() -> Optional[str]:
    return _get_env("AZURE_COSMOS_URI")


def get_azure_cosmos_key() -> Optional[str]:
    return _get_env("AZURE_COSMOS_KEY")


def get_azure_cosmos_db() -> Optional[str]:
    return _get_env("AZURE_COSMOS_DB")


def get_azure_cosmos_container() -> Optional[str]:
    return _get_env("AZURE_COSMOS_CONTAINER")


def get_vector_backend() -> str:
    backend = (_get_env("KNOWLEDGE_BACKEND") or "filesystem").lower()
    if backend == "firestore":
        return "bm25-firestore"
    return "bm25-filesystem"


@lru_cache(maxsize=1)
def config_snapshot() -> dict:
    """Return a cached snapshot of relevant env-driven config."""
    return {
        "tenant_id": get_tenant_id(),
        "env": get_env(),
        "nexus_backend": get_nexus_backend(),
        "raw_bucket": get_raw_bucket(),
        "datasets_bucket": get_datasets_bucket(),
        "gcp_project": get_firestore_project(),
        "region": get_region(),
        "vector_index_id": get_vector_index_id(),
        "vector_endpoint_id": get_vector_endpoint_id(),
        "vector_project": get_vector_project(),
        "storage_provider": get_storage_provider(),
        "storage_target": get_storage_target(),
        "memory_backend": get_memory_backend(),
        "model_provider": get_model_provider(),
        "allow_billable_vertex": allow_billable_vertex(),
        "azure_storage_account": get_azure_storage_account(),
        "azure_storage_container": get_azure_storage_container(),
        "azure_storage_key": get_azure_storage_key(),
        "azure_cosmos_uri": get_azure_cosmos_uri(),
        "azure_cosmos_key": get_azure_cosmos_key(),
        "azure_cosmos_db": get_azure_cosmos_db(),
        "azure_cosmos_container": get_azure_cosmos_container(),
        "vector_backend": get_vector_backend(),
    }
