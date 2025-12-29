"""Azure Cosmos DB memory stub with the new env contract."""
from __future__ import annotations

from typing import Optional

from engines.azure import COST_KILL_SWITCH_DOC


class AzureCosmosMemoryBackend:
    """Placeholder memory backend that fails until Cosmos wiring exists."""

    REQUIRED_ENVS = (
        "AZURE_COSMOS_URI",
        "AZURE_COSMOS_KEY",
        "AZURE_COSMOS_DB",
        "AZURE_COSMOS_CONTAINER",
    )

    def __init__(self, uri: Optional[str] = None, key: Optional[str] = None, database: Optional[str] = None, container: Optional[str] = None) -> None:
        self.uri = uri
        self.key = key
        self.database = database
        self.container = container
        self._fail_fast()

    def _fail_fast(self) -> None:
        envs = ", ".join(self.REQUIRED_ENVS)
        raise NotImplementedError(
            "Azure Cosmos memory backend is not implemented yet. "
            f"Plan the wiring with {envs} and review {COST_KILL_SWITCH_DOC}."
        )
