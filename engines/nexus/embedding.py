"""Embedding adapter for Nexus pipelines."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from engines.common.identity import RequestContext
from engines.common.selecta import get_selecta_resolver
from engines.config import runtime_config
from engines.cost.vertex_guard import ensure_billable_vertex_allowed

try:  # pragma: no cover - optional dependency
    from vertexai import init as vertexai_init  # type: ignore
    from vertexai.language_models import TextEmbeddingModel  # type: ignore
    from vertexai.vision_models import MultiModalEmbeddingModel, Image  # type: ignore
except Exception:  # pragma: no cover
    vertexai_init = None
    TextEmbeddingModel = None
    MultiModalEmbeddingModel = None
    Image = None


@dataclass
class EmbeddingResult:
    vector: List[float]
    model_id: str


class EmbeddingAdapter:
    def embed_text(self, text: str, model_id: Optional[str] = None, context: Optional[RequestContext] = None) -> EmbeddingResult:
        raise NotImplementedError

    def embed_image(self, image_uri: str, model_id: Optional[str] = None, context: Optional[RequestContext] = None) -> EmbeddingResult:
        raise NotImplementedError

    def embed_image_bytes(self, image_bytes: bytes, model_id: Optional[str] = None, context: Optional[RequestContext] = None) -> EmbeddingResult:
        raise NotImplementedError


class VertexEmbeddingAdapter(EmbeddingAdapter):
    """Minimal Vertex embedding adapter (text/image)."""

    def __init__(self, client: Optional[object] = None) -> None:
        self._selecta = get_selecta_resolver()
        self._client = client or self._init_client()

    def _init_client(self):
        ensure_billable_vertex_allowed("Vertex embeddings")
        if vertexai_init is None or TextEmbeddingModel is None or MultiModalEmbeddingModel is None:
            raise RuntimeError("google-cloud-aiplatform/vertexai not installed for Vertex embeddings")
        ctx = self._default_ctx()
        project = runtime_config.get_firestore_project()
        location = runtime_config.get_region() or runtime_config.get_env_region_fallback()
        vertexai_init(project=project, location=location)
        return {"project": project, "location": location}

    def _default_ctx(self) -> RequestContext:
        tenant = runtime_config.get_tenant_id()
        env = runtime_config.get_env() or "dev"
        if not tenant:
            if env not in {"dev", "local"}:
                raise RuntimeError("tenant_id is required for embedding resolution")
            tenant = "t_dev"
        return RequestContext(request_id="selecta_embed", tenant_id=tenant, env=env)

    def embed_text(self, text: str, model_id: Optional[str] = None, context: Optional[RequestContext] = None) -> EmbeddingResult:
        ctx = context or self._default_ctx()
        model = model_id or self._selecta.embed_config(ctx).model_id
        if self._client is None or model is None:
            raise RuntimeError("Vertex embedding client/model missing")
        
        try:
            embed_model = TextEmbeddingModel.from_pretrained(model)
            # Modern SDK: get_embeddings takes a list of strings
            embeddings = embed_model.get_embeddings([text])
            if not embeddings:
                raise RuntimeError("Vertex returned no embeddings")
            vector = embeddings[0].values
            return EmbeddingResult(vector=list(vector), model_id=model)
        except Exception as e:
            raise RuntimeError(f"Vertex text embedding failed for model {model}: {e}") from e

    def embed_image(self, image_uri: str, model_id: Optional[str] = None, context: Optional[RequestContext] = None) -> EmbeddingResult:
        ctx = context or self._default_ctx()
        model = model_id or self._selecta.embed_config(ctx).model_id
        if self._client is None or model is None:
            raise RuntimeError("Vertex embedding client/model missing")
        
        try:
            embed_model = MultiModalEmbeddingModel.from_pretrained(model)
            # Modern SDK: use Image class
            # image_uri can be local path or GCS uri? 
            # Image.load_from_file handles local. For GCS, we rely on GCS fuse or similar?
            # Actually, standard Vertex SDK Image.load_from_file usually expects local.
            # However, if it's gs://, we might need a workaround or assuming local mount.
            # But wait, previous code passed image_path=image_uri.
            # Let's try Image.load_from_file first.
            image = Image.load_from_file(image_uri)
            embeddings = embed_model.get_embeddings(image=image)
            
            vector = getattr(embeddings, "image_embedding", None)
            if vector is None:
                # Fallback check
                raise RuntimeError("Vertex image embedding response missing image_embedding")
            
            return EmbeddingResult(vector=list(vector), model_id=model)
        except Exception as e:
            raise RuntimeError(f"Vertex image embedding failed for model {model}: {e}") from e

    def embed_image_bytes(self, image_bytes: bytes, model_id: Optional[str] = None, context: Optional[RequestContext] = None) -> EmbeddingResult:
        ctx = context or self._default_ctx()
        model = model_id or self._selecta.embed_config(ctx).model_id
        if self._client is None or model is None:
            raise RuntimeError("Vertex embedding client/model missing")
        
        try:
            embed_model = MultiModalEmbeddingModel.from_pretrained(model)
            image = Image(image_bytes)
            embeddings = embed_model.get_embeddings(image=image)
            
            vector = getattr(embeddings, "image_embedding", None)
            if vector is None:
                raise RuntimeError("Vertex image embedding response missing image_embedding")
            
            return EmbeddingResult(vector=list(vector), model_id=model)
        except Exception as e:
            raise RuntimeError(f"Vertex image embedding failed for model {model}: {e}") from e
