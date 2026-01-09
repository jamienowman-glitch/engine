"""Run Memory service rejection (dummy implementation)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from engines.common.identity import RequestContext
from engines.run_memory.cloud_run_memory import (
    VersionConflictError,
)

class RunMemoryServiceReject:
    """Rejects all run memory operations."""

    def __init__(self, context: RequestContext) -> None:
        self._context = context

    def write(
        self,
        key: str,
        value: Any,
        run_id: str,
        expected_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Reject write."""
        raise RuntimeError("Run Memory not enabled for this tenant/env.")

    def read(
        self,
        key: str,
        run_id: str,
        version: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Reject read."""
        raise RuntimeError("Run Memory not enabled for this tenant/env.")

    def list_keys(self, run_id: str) -> List[str]:
        """Reject list_keys."""
        raise RuntimeError("Run Memory not enabled for this tenant/env.")
