"""BigQuery-backed Nexus backend for DatasetEvents."""
from __future__ import annotations

import datetime
from typing import Any, Dict, Optional

from engines.config import runtime_config


class BigQueryNexusBackend:
    def __init__(self, client: Optional[Any] = None, dataset: Optional[str] = None, table: Optional[str] = None) -> None:
        self._dataset = dataset or runtime_config.get_nexus_bq_dataset() or "nexus_events"
        self._table = table or runtime_config.get_nexus_bq_table() or "dataset_events"
        if client:
            self._client = client
        else:
            try:  # pragma: no cover - optional dependency
                from google.cloud import bigquery  # type: ignore
            except Exception as exc:  # pragma: no cover
                raise RuntimeError("google-cloud-bigquery not installed") from exc
            self._client = bigquery.Client()  # type: ignore[call-arg]

    def _table_ref(self):
        return f"{self._dataset}.{self._table}"

    def write_event(self, event) -> Dict[str, Any]:
        payload = event.model_dump()
        payload["ingested_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        try:
            errors = self._client.insert_rows_json(self._table_ref(), [payload])  # type: ignore[arg-type]
            if errors:
                return {"status": "error", "errors": errors}
            return {"status": "accepted"}
        except Exception as exc:
            # Degrade gracefully; caller can log/inspect without crashing pipeline.
            return {"status": "error", "exception": exc.__class__.__name__, "message": str(exc)}
