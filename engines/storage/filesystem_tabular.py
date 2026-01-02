"""Filesystem-backed tabular store adapter for policies/hard-facts (Lane 2 adapter).

Stores semi-structured data (JSONL) with simple key/value interface.
Location: var/tabular_store/{tenant_id}/{env}/{surface_id or "_"}/
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from engines.common.identity import RequestContext
from engines.common.surface_normalizer import normalize_surface_id

logger = logging.getLogger(__name__)


class FileSystemTabularStore:
    """Filesystem-backed tabular store using JSONL files.
    
    Path structure:
      var/tabular_store/{tenant_id}/{env}/{surface_id or "_"}/{table_name}.jsonl
    
    Each line is: {"key": "<key>", "data": <json>, "timestamp": "ISO-8601"}
    """
    
    def __init__(self, base_dir: Optional[str | Path] = None) -> None:
        self._base_dir = Path(base_dir or Path.cwd() / "var" / "tabular_store")
        self._base_dir.mkdir(parents=True, exist_ok=True)
    
    def _table_dir(self, context: RequestContext) -> Path:
        """Deterministic directory path for tabular data."""
        surface = normalize_surface_id(context.surface_id) if context.surface_id else "_"
        env = (context.env or "dev").lower()
        tenant = context.tenant_id
        
        return self._base_dir / tenant / env / surface
    
    def _table_file(self, table_name: str, context: RequestContext) -> Path:
        """Full path to a table's JSONL file."""
        safe_name = table_name.replace("/", "_").replace("..", "_")
        return self._table_dir(context) / f"{safe_name}.jsonl"
    
    def upsert(
        self, 
        table_name: str, 
        key: str, 
        data: Dict[str, Any],
        context: RequestContext,
    ) -> None:
        """Upsert a record (update if exists, insert if new).
        
        Implementation: rewrite entire file (simple JSONL, not too large typically).
        """
        # Enforce backend-class guard: filesystem forbidden in sellable modes
        from engines.routing.manager import ForbiddenBackendClass, SELLABLE_MODES
        mode_lower = (context.mode or "lab").lower()
        if mode_lower in SELLABLE_MODES:
            raise ForbiddenBackendClass(
                f"[FORBIDDEN_BACKEND_CLASS] Backend 'filesystem' is forbidden in mode '{context.mode}' "
                f"(resource_kind=tabular_store, tenant={context.tenant_id}, env={context.env}). "
                f"Sellable modes require cloud backends. Use 'lab' mode for filesystem."
            )
        
        table_dir = self._table_dir(context)
        table_dir.mkdir(parents=True, exist_ok=True)
        
        table_file = self._table_file(table_name, context)
        
        # Read all records, find and update or append
        records = {}
        if table_file.exists():
            try:
                with open(table_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            records[record.get("key")] = record
                        except Exception as exc:
                            logger.warning(f"Skipping malformed line in {table_file}: {exc}")
            except Exception as exc:
                logger.warning(f"Failed to read {table_file}: {exc}")
        
        # Update or insert
        from datetime import datetime, timezone
        records[key] = {
            "key": key,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Rewrite entire file
        try:
            with open(table_file, "w") as f:
                for record in records.values():
                    f.write(json.dumps(record) + "\n")
        except Exception as exc:
            logger.error(f"Failed to upsert to {table_file}: {exc}")
            raise RuntimeError(f"Tabular upsert failed: {exc}") from exc
    
    def get(
        self, 
        table_name: str, 
        key: str, 
        context: RequestContext,
    ) -> Optional[Dict[str, Any]]:
        """Get a record by key."""
        # Enforce backend-class guard: filesystem forbidden in sellable modes
        from engines.routing.manager import ForbiddenBackendClass, SELLABLE_MODES
        mode_lower = (context.mode or "lab").lower()
        if mode_lower in SELLABLE_MODES:
            raise ForbiddenBackendClass(
                f"[FORBIDDEN_BACKEND_CLASS] Backend 'filesystem' is forbidden in mode '{context.mode}' "
                f"(resource_kind=tabular_store, tenant={context.tenant_id}, env={context.env}). "
                f"Sellable modes require cloud backends. Use 'lab' mode for filesystem."
            )
        
        table_file = self._table_file(table_name, context)
        
        if not table_file.exists():
            return None
        
        try:
            with open(table_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if record.get("key") == key:
                            return record.get("data")
                    except Exception:
                        continue
        except Exception as exc:
            logger.error(f"Failed to read from {table_file}: {exc}")
        
        return None
    
    def list_by_prefix(
        self, 
        table_name: str, 
        key_prefix: str,
        context: RequestContext,
    ) -> list[Dict[str, Any]]:
        """List records with keys matching prefix."""
        # Enforce backend-class guard: filesystem forbidden in sellable modes
        from engines.routing.manager import ForbiddenBackendClass, SELLABLE_MODES
        mode_lower = (context.mode or "lab").lower()
        if mode_lower in SELLABLE_MODES:
            raise ForbiddenBackendClass(
                f"[FORBIDDEN_BACKEND_CLASS] Backend 'filesystem' is forbidden in mode '{context.mode}' "
                f"(resource_kind=tabular_store, tenant={context.tenant_id}, env={context.env}). "
                f"Sellable modes require cloud backends. Use 'lab' mode for filesystem."
            )
        
        table_file = self._table_file(table_name, context)
        
        if not table_file.exists():
            return []
        
        results = []
        try:
            with open(table_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if record.get("key", "").startswith(key_prefix):
                            results.append(record.get("data"))
                    except Exception:
                        continue
        except Exception as exc:
            logger.error(f"Failed to read from {table_file}: {exc}")
        
        return results
    
    def delete(
        self, 
        table_name: str, 
        key: str, 
        context: RequestContext,
    ) -> None:
        """Delete a record by key (rewrite file without it)."""
        # Enforce backend-class guard: filesystem forbidden in sellable modes
        from engines.routing.manager import ForbiddenBackendClass, SELLABLE_MODES
        mode_lower = (context.mode or "lab").lower()
        if mode_lower in SELLABLE_MODES:
            raise ForbiddenBackendClass(
                f"[FORBIDDEN_BACKEND_CLASS] Backend 'filesystem' is forbidden in mode '{context.mode}' "
                f"(resource_kind=tabular_store, tenant={context.tenant_id}, env={context.env}). "
                f"Sellable modes require cloud backends. Use 'lab' mode for filesystem."
            )
        
        table_file = self._table_file(table_name, context)
        
        if not table_file.exists():
            return
        
        # Read all records except the one to delete
        records_to_keep = []
        try:
            with open(table_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if record.get("key") != key:
                            records_to_keep.append(record)
                    except Exception:
                        pass
        except Exception as exc:
            logger.warning(f"Failed to read {table_file} for delete: {exc}")
        
        # Rewrite file
        try:
            with open(table_file, "w") as f:
                for record in records_to_keep:
                    f.write(json.dumps(record) + "\n")
        except Exception as exc:
            logger.error(f"Failed to delete from {table_file}: {exc}")
