"""Cloud backend implementations for run_memory (persistent shared coordination state).

Supports Firestore, DynamoDB, Cosmos backends with versioning.
Enforces optimistic concurrency (version-based conflict detection).
Scope: tenant / mode / project / run.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from uuid import uuid4

from engines.common.identity import RequestContext

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    """Return current timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


class VersionConflictError(Exception):
    """Raised when version check fails (optimistic concurrency conflict)."""
    pass


# ===== Firestore Implementation =====

class FirestoreRunMemory:
    """Firestore-backed persistent run memory with versioning."""

    _collection = "run_memory"

    def __init__(self, project: Optional[str] = None, client: Optional[object] = None) -> None:
        try:
            from google.cloud import firestore
        except Exception as exc:
            raise RuntimeError("google-cloud-firestore is required for Firestore run memory") from exc

        from engines.config import runtime_config

        self._project = project or runtime_config.get_firestore_project()
        if not self._project:
            raise RuntimeError("GCP project is required for Firestore run memory")
        self._client = client or firestore.Client(project=self._project)

    def _document_id(self, tenant_id: str, mode: str, project_id: str, run_id: str, key: str) -> str:
        """Generate document ID from scope."""
        project = project_id or "shared"
        return f"{tenant_id}#{mode}#{project}#{run_id}#{key}"

    def write(
        self,
        key: str,
        value: Any,
        context: RequestContext,
        run_id: str,
        expected_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Write a value to run memory with optimistic concurrency.

        Args:
            key: run memory key
            value: any serializable value
            context: request context
            run_id: provenance identifier
            expected_version: if provided, only write if current version matches

        Returns: dict with key, value, version, created_by, created_at, updated_by, updated_at
        Raises: VersionConflictError if version mismatch
        """
        if not key or not run_id:
            raise ValueError("key and run_id are required")
        if not context.user_id:
            raise ValueError("user_id is required (from context)")

        doc_id = self._document_id(context.tenant_id, context.mode, context.project_id, run_id, key)

        # Read current document to check version
        try:
            doc = self._client.collection(self._collection).document(doc_id).get()
            current_version = 0

            if doc.exists:
                current_version = doc.to_dict().get("version", 0)

                # Check optimistic concurrency
                if expected_version is not None and expected_version != current_version:
                    raise VersionConflictError(
                        f"Version conflict for key '{key}': expected {expected_version}, "
                        f"got {current_version}. Concurrent update detected."
                    )

            # Write new version
            new_version = current_version + 1
            now = _now_iso()
            created_by = context.user_id
            created_at = now

            if doc.exists:
                doc_dict = doc.to_dict()
                created_by = doc_dict.get("created_by", context.user_id)
                created_at = doc_dict.get("created_at", now)

            doc_data = {
                "key": key,
                "value": value,
                "tenant_id": context.tenant_id,
                "mode": context.mode,
                "project_id": context.project_id,
                "run_id": run_id,
                "version": new_version,
                "created_by": created_by,
                "created_at": created_at,
                "updated_by": context.user_id,
                "updated_at": now,
            }

            self._client.collection(self._collection).document(doc_id).set(doc_data)
            logger.debug(f"Wrote run memory key '{key}' (version {new_version}, run {run_id})")
            return {
                "key": key,
                "value": value,
                "version": new_version,
                "created_by": created_by,
                "created_at": created_at,
                "updated_by": context.user_id,
                "updated_at": now,
            }
        except VersionConflictError:
            raise
        except Exception as exc:
            logger.error(f"Failed to write run memory key '{key}': {exc}")
            raise RuntimeError(f"Run memory write failed: {exc}") from exc

    def read(
        self,
        key: str,
        context: RequestContext,
        run_id: str,
        version: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Read a value from run memory (latest or specific version).

        Returns dict with: value, version, created_by, created_at, updated_by, updated_at
        Returns None if not found.
        """
        if not key or not run_id:
            raise ValueError("key and run_id are required")

        doc_id = self._document_id(context.tenant_id, context.mode, context.project_id, run_id, key)

        try:
            doc = self._client.collection(self._collection).document(doc_id).get()

            if not doc.exists:
                return None

            data = doc.to_dict()

            # If version requested, check match
            if version is not None and data.get("version") != version:
                logger.debug(f"Version {version} not found for key '{key}' (current: {data.get('version')})")
                return None

            return {
                "value": data.get("value"),
                "version": data.get("version"),
                "created_by": data.get("created_by"),
                "created_at": data.get("created_at"),
                "updated_by": data.get("updated_by"),
                "updated_at": data.get("updated_at"),
            }
        except Exception as exc:
            logger.error(f"Failed to read run memory key '{key}': {exc}")
            return None

    def list_keys(
        self,
        context: RequestContext,
        run_id: str,
    ) -> List[str]:
        """List all keys in run memory for a run."""
        try:
            docs = (
                self._client.collection(self._collection)
                .where("tenant_id", "==", context.tenant_id)
                .where("mode", "==", context.mode)
                .where("run_id", "==", run_id)
            )

            if context.project_id:
                docs = docs.where("project_id", "==", context.project_id)

            keys = []
            for doc in docs.stream():
                key = doc.to_dict().get("key")
                if key:
                    keys.append(key)

            return keys
        except Exception as exc:
            logger.error(f"Failed to list run memory keys for run {run_id}: {exc}")
            return []


# ===== DynamoDB Implementation =====

class DynamoDBRunMemory:
    """DynamoDB-backed persistent run memory with versioning."""

    def __init__(self, table_name: Optional[str] = None, region: Optional[str] = None) -> None:
        try:
            import boto3
        except Exception as exc:
            raise RuntimeError("boto3 is required for DynamoDB run memory") from exc

        self._table_name = table_name or "run_memory"
        self._region = region or "us-west-2"

        try:
            dynamodb = boto3.resource("dynamodb", region_name=self._region)
            self._table = dynamodb.Table(self._table_name)
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize DynamoDB table: {exc}") from exc

    def _pk(self, tenant_id: str, mode: str, run_id: str) -> str:
        """Generate partition key."""
        return f"{tenant_id}#{mode}#{run_id}"

    def _sk(self, project_id: Optional[str], key: str) -> str:
        """Generate sort key."""
        project = project_id or "shared"
        return f"{project}#{key}"

    def write(
        self,
        key: str,
        value: Any,
        context: RequestContext,
        run_id: str,
        expected_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Write a value to run memory with optimistic concurrency."""
        if not key or not run_id:
            raise ValueError("key and run_id are required")
        if not context.user_id:
            raise ValueError("user_id is required (from context)")

        pk = self._pk(context.tenant_id, context.mode, run_id)
        sk = self._sk(context.project_id, key)

        try:
            # Read current version
            response = self._table.get_item(Key={"pk": pk, "sk": sk})
            current_version = 0
            created_at = _now_iso()
            created_by = context.user_id

            if "Item" in response:
                current_version = response["Item"].get("version", 0)
                created_at = response["Item"].get("created_at", _now_iso())
                created_by = response["Item"].get("created_by", context.user_id)

                # Check optimistic concurrency
                if expected_version is not None and expected_version != current_version:
                    raise VersionConflictError(
                        f"Version conflict for key '{key}': expected {expected_version}, "
                        f"got {current_version}. Concurrent update detected."
                    )

            # Write new version
            new_version = current_version + 1
            now = _now_iso()
            item = {
                "pk": pk,
                "sk": sk,
                "key": key,
                "value": json.dumps(value) if not isinstance(value, str) else value,
                "tenant_id": context.tenant_id,
                "mode": context.mode,
                "project_id": context.project_id or "shared",
                "run_id": run_id,
                "version": new_version,
                "created_by": created_by,
                "created_at": created_at,
                "updated_by": context.user_id,
                "updated_at": now,
            }

            self._table.put_item(Item=item)
            logger.debug(f"Wrote run memory key '{key}' (version {new_version}, run {run_id})")
            return {
                "key": key,
                "value": value,
                "version": new_version,
                "created_by": created_by,
                "created_at": created_at,
                "updated_by": context.user_id,
                "updated_at": now,
            }
        except VersionConflictError:
            raise
        except Exception as exc:
            logger.error(f"Failed to write run memory key '{key}': {exc}")
            raise RuntimeError(f"Run memory write failed: {exc}") from exc

    def read(
        self,
        key: str,
        context: RequestContext,
        run_id: str,
        version: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Read a value from run memory (latest or specific version)."""
        if not key or not run_id:
            raise ValueError("key and run_id are required")

        pk = self._pk(context.tenant_id, context.mode, run_id)
        sk = self._sk(context.project_id, key)

        try:
            response = self._table.get_item(Key={"pk": pk, "sk": sk})

            if "Item" not in response:
                return None

            item = response["Item"]

            # If version requested, check match
            if version is not None and item.get("version") != version:
                logger.debug(f"Version {version} not found for key '{key}' (current: {item.get('version')})")
                return None

            value = item.get("value")
            # Try to parse if JSON string
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except:
                    pass

            return {
                "value": value,
                "version": item.get("version"),
                "created_by": item.get("created_by"),
                "created_at": item.get("created_at"),
                "updated_by": item.get("updated_by"),
                "updated_at": item.get("updated_at"),
            }
        except Exception as exc:
            logger.error(f"Failed to read run memory key '{key}': {exc}")
            return None

    def list_keys(
        self,
        context: RequestContext,
        run_id: str,
    ) -> List[str]:
        """List all keys in run memory for a run."""
        try:
            pk = self._pk(context.tenant_id, context.mode, run_id)

            response = self._table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": pk},
            )

            keys = []
            for item in response.get("Items", []):
                key = item.get("key")
                if key:
                    keys.append(key)

            return keys
        except Exception as exc:
            logger.error(f"Failed to list run memory keys for run {run_id}: {exc}")
            return []


# ===== Cosmos DB Implementation =====

class CosmosRunMemory:
    """Cosmos DB-backed persistent run memory with versioning."""

    def __init__(self, endpoint: str, key: str, database: str = "run_memory") -> None:
        try:
            from azure.cosmos import CosmosClient
        except Exception as exc:
            raise RuntimeError("azure-cosmos is required for Cosmos run memory") from exc

        try:
            self._client = CosmosClient(endpoint, credential=key)
            self._database = self._client.get_database_client(database)
            self._container = self._database.get_container_client("shared_state")
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize Cosmos client: {exc}") from exc

    def _document_id(self, tenant_id: str, mode: str, project_id: str, run_id: str, key: str) -> str:
        """Generate document ID from scope."""
        project = project_id or "shared"
        return f"{tenant_id}#{mode}#{project}#{run_id}#{key}"

    def write(
        self,
        key: str,
        value: Any,
        context: RequestContext,
        run_id: str,
        expected_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Write a value to run memory with optimistic concurrency."""
        if not key or not run_id:
            raise ValueError("key and run_id are required")
        if not context.user_id:
            raise ValueError("user_id is required (from context)")

        doc_id = self._document_id(context.tenant_id, context.mode, context.project_id, run_id, key)

        try:
            # Try to read current document
            try:
                current_doc = self._container.read_item(
                    item=doc_id,
                    partition_key=run_id,
                )
                current_version = current_doc.get("version", 0)
                created_at = current_doc.get("created_at", _now_iso())
                created_by = current_doc.get("created_by", context.user_id)

                # Check optimistic concurrency
                if expected_version is not None and expected_version != current_version:
                    raise VersionConflictError(
                        f"Version conflict for key '{key}': expected {expected_version}, "
                        f"got {current_version}. Concurrent update detected."
                    )
            except:
                # Document doesn't exist yet
                current_version = 0
                created_at = _now_iso()
                created_by = context.user_id

            # Write new version
            new_version = current_version + 1
            now = _now_iso()
            doc_data = {
                "id": doc_id,
                "partition_key": run_id,
                "key": key,
                "value": value,
                "tenant_id": context.tenant_id,
                "mode": context.mode,
                "project_id": context.project_id,
                "run_id": run_id,
                "version": new_version,
                "created_by": created_by,
                "created_at": created_at,
                "updated_by": context.user_id,
                "updated_at": now,
            }

            self._container.upsert_item(body=doc_data)
            logger.debug(f"Wrote run memory key '{key}' (version {new_version}, run {run_id})")
            return {
                "key": key,
                "value": value,
                "version": new_version,
                "created_by": created_by,
                "created_at": created_at,
                "updated_by": context.user_id,
                "updated_at": now,
            }
        except VersionConflictError:
            raise
        except Exception as exc:
            logger.error(f"Failed to write run memory key '{key}': {exc}")
            raise RuntimeError(f"Run memory write failed: {exc}") from exc

    def read(
        self,
        key: str,
        context: RequestContext,
        run_id: str,
        version: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Read a value from run memory (latest or specific version)."""
        if not key or not run_id:
            raise ValueError("key and run_id are required")

        doc_id = self._document_id(context.tenant_id, context.mode, context.project_id, run_id, key)

        try:
            doc = self._container.read_item(item=doc_id, partition_key=run_id)

            # If version requested, check match
            if version is not None and doc.get("version") != version:
                logger.debug(f"Version {version} not found for key '{key}' (current: {doc.get('version')})")
                return None

            return {
                "value": doc.get("value"),
                "version": doc.get("version"),
                "created_by": doc.get("created_by"),
                "created_at": doc.get("created_at"),
                "updated_by": doc.get("updated_by"),
                "updated_at": doc.get("updated_at"),
            }
        except:
            return None

    def list_keys(
        self,
        context: RequestContext,
        run_id: str,
    ) -> List[str]:
        """List all keys in run memory for a run."""
        try:
            query = "SELECT c.key FROM c WHERE c.run_id = @run_id"
            params = [{"name": "@run_id", "value": run_id}]

            if context.tenant_id:
                query += " AND c.tenant_id = @tenant_id"
                params.append({"name": "@tenant_id", "value": context.tenant_id})

            keys = []
            for item in self._container.query_items(query=query, parameters=params):
                key = item.get("key")
                if key:
                    keys.append(key)

            return keys
        except Exception as exc:
            logger.error(f"Failed to list run memory keys for run {run_id}: {exc}")
            return []
