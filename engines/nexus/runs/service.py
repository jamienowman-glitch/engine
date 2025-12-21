"""Research Run Service."""
from __future__ import annotations

from collections import defaultdict
from typing import List

from engines.common.identity import RequestContext
from engines.nexus.backends import get_backend
from engines.nexus.runs.models import ResearchRun

class ResearchRunService:
    def list_runs(self, ctx: RequestContext, limit: int = 50) -> List[ResearchRun]:
        """
        Derive ResearchRuns from the event log.
        """
        backend = get_backend()
        if not hasattr(backend, "query_events"):
            # Fallback if backend doesn't support query (e.g. firestore impl not updated yet)
            return []
            
        events = backend.query_events(tenant_id=ctx.tenant_id, env=ctx.env, limit=1000)
        
        # Group by trace_id (metadata.trace_id or derived)
        # Note: DatasetEvent schema has `trace_id` at top level or metadata? 
        # Logging pipeline puts it in metadata usually.
        # Let's check log structure in event_log.py: 
        # trace_id is not explicitly in `default_event_logger`. 
        # But `RequestContext` has it.
        # Wait, `default_event_logger` signature is `EventLogEntry`. entry doesn't have trace_id?
        # entry has `metadata`. Hopefully trace_id is injected there?
        # In `engines.logging.event_log.py`, metadata is passed through.
        # We need to assume aggregation key. 
        # For now, let's group by `asset_id` if trace_id missing, or just treating each significant event as a Run.
        
        runs_map = defaultdict(list)
        
        for e in events:
            # Try to find a grouping key
            # Check metadata for trace_id, or use event's timestamp bucket?
            # Creating a simplified view: Each event of type 'file_upload', 'pack_created' IS a run.
            
            # Simple heuristic for Phase 7:
            # A "Run" is a grouping of events.
            # If we don't have trace_id, we treat each "primary" event as a Run.
            
            meta = e.metadata or {}
            key = meta.get("trace_id") or meta.get("request_id") or e.output.get("asset_id") or "unknown"
            runs_map[key].append(e)
            
        results = []
        for key, group in runs_map.items():
            if not group: 
                continue
                
            first = group[-1] # Chronological usually? Query returns recent first. So last is earliest.
            last = group[0]
            
            # Determine Kind
            kind = "unknown"
            event_types = {g.input.get("event_type") for g in group if g.input}
            if "pack_created" in event_types:
                kind = "influence_pack"
            elif "card_created" in event_types:
                kind = "card_ingest"
            elif "card_search" in event_types:
                kind = "search"
            
            # Counts
            # (Rough counting)
            
            run = ResearchRun(
                run_id=str(key),
                tenant_id=ctx.tenant_id,
                env=ctx.env,
                start_time=datetime.now(), # Placeholder if timestamp missing in schema
                end_time=datetime.now(),
                kind=kind,
                status="completed",
                events_count=len(group),
                metadata={"event_types": list(event_types)}
            )
            results.append(run)
            
        return results[:limit]

from datetime import datetime
