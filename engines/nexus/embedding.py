"""Embedding adapter for Nexus pipelines."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from engines.config import runtime_config

try:  # pragma: no cover - optional dependency
    from google.cloud import aiplatform  # type: ignore
except Exception:  # pragma: no cover
    aiplatform = None


@dataclass
class EmbeddingResult:
    vector: List[float]
    model_id: str


class EmbeddingAdapter:
    def embed_text(self, text: str, model_id: Optional[str] = None) -> EmbeddingResult:
        raise NotImplementedError

    def embed_image(self, image_uri: str, model_id: Optional[str] = None) -> EmbeddingResult:
        raise NotImplementedError

    def embed_image_bytes(self, image_bytes: bytes, model_id: Optional[str] = None) -> EmbeddingResult:
        raise NotImplementedError


class VertexEmbeddingAdapter(EmbeddingAdapter):
    """Minimal Vertex embedding adapter (text/image)."""

    def __init__(self, client: Optional[object] = None) -> None:
        self._client = client or self._init_client()

    def _init_client(self):
        if aiplatform is None:
            raise RuntimeError("google-cloud-aiplatform not installed for Vertex embeddings")
        project = runtime_config.get_firestore_project()
        location = runtime_config.get_region() or "us-central1"
        aiplatform.init(project=project, location=location)
        return aiplatform

    def embed_text(self, text: str, model_id: Optional[str] = None) -> EmbeddingResult:
        model = model_id or runtime_config.get_text_embedding_model_id()
        if self._client is None or model is None:
            raise RuntimeError("Vertex embedding client/model missing")
        embed_model = self._client.TextEmbeddingModel(model_name=model)  # type: ignore[attr-defined]
        response = embed_model.get_embeddings([text])  # type: ignore[call-arg]
        vector = getattr(response[0], "values", None) if response else None
        if vector is None:
            raise RuntimeError("Vertex embedding response missing values")
        return EmbeddingResult(vector=list(vector), model_id=model)

    def embed_image(self, image_uri: str, model_id: Optional[str] = None) -> EmbeddingResult:
        model = model_id or runtime_config.get_image_embedding_model_id()
        if self._client is None or model is None:
            raise RuntimeError("Vertex embedding client/model missing")
        embed_model = self._client.MultiModalEmbeddingModel(model_name=model)  # type: ignore[attr-defined]
        response = embed_model.get_embeddings(image_path=image_uri)  # type: ignore[call-arg]
        vector = getattr(response, "image_embedding", None)
        if vector is None:
            raise RuntimeError("Vertex image embedding response missing values")
        values = getattr(vector, "values", None)
        if values is None:
            raise RuntimeError("Vertex image embedding missing values array")
        return EmbeddingResult(vector=list(values), model_id=model)

    def embed_image_bytes(self, image_bytes: bytes, model_id: Optional[str] = None) -> EmbeddingResult:
        model = model_id or runtime_config.get_image_embedding_model_id()
        if self._client is None or model is None:
            raise RuntimeError("Vertex embedding client/model missing")
        embed_model = self._client.MultiModalEmbeddingModel(model_name=model)  # type: ignore[attr-defined]
        response = embed_model.get_embeddings(image_bytes=image_bytes)  # type: ignore[call-arg]
        vector = getattr(response, "image_embedding", None)
        if vector is None:
            raise RuntimeError("Vertex image embedding response missing values")
        values = getattr(vector, "values", None)
        if values is None:
            raise RuntimeError("Vertex image embedding missing values array")
        return EmbeddingResult(vector=list(values), model_id=model)
