"""Azure Blob storage stub with explicit env-contract errors."""
from __future__ import annotations

from typing import Optional

from engines.azure import COST_KILL_SWITCH_DOC


class AzureBlobStorageAdapter:
    """Placeholder adapter that fails until storage wiring is added."""

    REQUIRED_ENVS = (
        "AZURE_STORAGE_ACCOUNT",
        "AZURE_STORAGE_CONTAINER",
        "AZURE_STORAGE_KEY",
    )

    def __init__(self, account: Optional[str] = None, container: Optional[str] = None, credential: Optional[str] = None) -> None:
        self.account = account
        self.container = container
        self.credential = credential
        self._fail_fast()

    def _fail_fast(self) -> None:
        vars_list = ", ".join(self.REQUIRED_ENVS)
        raise NotImplementedError(
            "Azure Blob storage adapter is not implemented yet. "
            f"Plan the wiring with {vars_list} and review {COST_KILL_SWITCH_DOC}."
        )
