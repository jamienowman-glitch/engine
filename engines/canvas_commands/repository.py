from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Tuple, Protocol
from engines.canvas_commands.models import CanvasRevision, CanvasOp, _now

class CommandRepository(Protocol):
    async def get_head(self, canvas_id: str) -> CanvasRevision:
        ...

    async def get_ops_since(self, canvas_id: str, since_rev: int) -> List[CanvasOp]:
        ...

    async def check_idempotency(self, key: str) -> Optional[int]:
        ...

    async def append_ops(
        self, 
        canvas_id: str, 
        expected_rev: int, 
        ops: List[CanvasOp],
        idempotency_key: Optional[str] = None
    ) -> Tuple[bool, int, List[CanvasOp]]:
        ...

class InMemoryCommandRepository:
    def __init__(self):
        # canvas_id -> CanvasRevision
        self._heads: Dict[str, CanvasRevision] = {}
        # canvas_id -> List[(rev, [ops])] - Ordered log
        self._op_log: Dict[str, List[Tuple[int, List[CanvasOp]]]] = {}
        # idempotency_key -> (head_rev, timestamp)
        self._idempotency: Dict[str, Tuple[int, float]] = {}
        self._lock = asyncio.Lock()

    async def get_head(self, canvas_id: str) -> CanvasRevision:
        if canvas_id not in self._heads:
            # Initialize 0
            self._heads[canvas_id] = CanvasRevision(canvas_id=canvas_id, head_rev=0)
        return self._heads[canvas_id]

    async def get_ops_since(self, canvas_id: str, since_rev: int) -> List[CanvasOp]:
        """Fetch all ops committed AFTER since_rev."""
        log = self._op_log.get(canvas_id, [])
        all_ops = []
        for rev, ops in log:
            if rev > since_rev:
                all_ops.extend(ops)
        return all_ops

    async def check_idempotency(self, key: str) -> Optional[int]:
        if key in self._idempotency:
            return self._idempotency[key][0]
        return None

    async def append_ops(
        self, 
        canvas_id: str, 
        expected_rev: int, 
        ops: List[CanvasOp],
        idempotency_key: Optional[str] = None
    ) -> Tuple[bool, int, List[CanvasOp]]:
        """
        Atomic check-and-set.
        Returns (success, new_head_rev, recovery_ops_if_failed)
        """
        async with self._lock:
            if idempotency_key and idempotency_key in self._idempotency:
                return True, self._idempotency[idempotency_key][0], []

            head = await self.get_head(canvas_id)
            
            if head.head_rev != expected_rev:
                # Conflict!
                recovery = await self.get_ops_since(canvas_id, expected_rev)
                return False, head.head_rev, recovery
            
            # Apply
            new_rev = head.head_rev + 1
            head.head_rev = new_rev
            head.updated_at = _now() 
            
            self._op_log.setdefault(canvas_id, []).append((new_rev, ops))
            
            if idempotency_key:
                from datetime import datetime, timezone
                self._idempotency[idempotency_key] = (new_rev, datetime.now(timezone.utc).timestamp())
                
            return True, new_rev, []

# Singleton for Phase 04 - Typed as CommandRepository
command_repo: CommandRepository = InMemoryCommandRepository()
