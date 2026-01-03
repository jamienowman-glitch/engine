"""Diagnostics service with warning-first behavior for missing routes (Agent A - A-6).

Startup proceeds with warnings for missing:
- event_spine
- memory_store
- blackboard_store

Operations refuse silent fallback (no in-memory, no filesystem).
No startup failure; only warnings logged.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from engines.common.identity import RequestContext
from engines.routing.registry import routing_registry

logger = logging.getLogger(__name__)


class RouteHealthStatus:
    """Status of a resource route."""
    
    def __init__(self, resource_kind: str, is_configured: bool, backend_type: Optional[str] = None):
        self.resource_kind = resource_kind
        self.is_configured = is_configured
        self.backend_type = backend_type
    
    def __repr__(self) -> str:
        status = "✓" if self.is_configured else "✗"
        backend = f" ({self.backend_type})" if self.backend_type else ""
        return f"{status} {self.resource_kind}{backend}"


class EnginesDiagnosticsService:
    """Diagnostics for Agent A critical resources (A-6).
    
    Checks route configuration at startup and operation time.
    Warning-first: missing routes warn but don't crash startup.
    Operations refuse fallback (fail with error, not silent skip).
    """
    
    CRITICAL_RESOURCES = [
        "event_spine",
        "memory_store",
        "blackboard_store",
    ]
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._warnings: List[str] = []
        self._startup_warnings_logged = False
    
    def check_routes(self) -> Dict[str, RouteHealthStatus]:
        """Check all critical routes; log warnings if missing.
        
        Returns dict of resource_kind -> RouteHealthStatus.
        Logs warnings for missing routes but does NOT raise.
        """
        statuses = {}
        registry = routing_registry()
        
        for resource_kind in self.CRITICAL_RESOURCES:
            try:
                route = registry.get_route(
                    resource_kind=resource_kind,
                    tenant_id=self._context.tenant_id,
                    env=self._context.env,
                    project_id=self._context.project_id,
                )
                
                if route:
                    statuses[resource_kind] = RouteHealthStatus(
                        resource_kind=resource_kind,
                        is_configured=True,
                        backend_type=route.backend_type,
                    )
                    logger.info(
                        f"Route check: {resource_kind} configured with backend={route.backend_type}"
                    )
                else:
                    statuses[resource_kind] = RouteHealthStatus(
                        resource_kind=resource_kind,
                        is_configured=False,
                    )
                    warning = (
                        f"Route missing for {resource_kind} in tenant={self._context.tenant_id}, "
                        f"env={self._context.env}. Configure via /routing/routes. "
                        f"Operations will refuse fallback and log errors."
                    )
                    self._warnings.append(warning)
                    logger.warning(warning)
            except Exception as e:
                statuses[resource_kind] = RouteHealthStatus(
                    resource_kind=resource_kind,
                    is_configured=False,
                )
                warning = f"Failed to check route for {resource_kind}: {e}"
                self._warnings.append(warning)
                logger.warning(warning)
        
        return statuses
    
    def get_startup_diagnostics(self) -> str:
        """Get startup diagnostics message (warning-first)."""
        statuses = self.check_routes()
        
        lines = ["Engines Diagnostics (Agent A):"]
        missing = []
        
        for resource_kind in self.CRITICAL_RESOURCES:
            status = statuses.get(resource_kind)
            if status:
                lines.append(f"  {status}")
                if not status.is_configured:
                    missing.append(resource_kind)
        
        if missing:
            lines.append("")
            lines.append(f"⚠ Warning: {len(missing)} route(s) missing:")
            for resource in missing:
                lines.append(f"    - {resource}")
            lines.append("")
            lines.append("Startup will proceed. Operations on missing routes will be refused.")
        
        return "\n".join(lines)
    
    def assert_route_exists(self, resource_kind: str) -> None:
        """Assert that a route is configured; raise if missing.
        
        Used at operation time (not startup).
        Operations that require a route MUST call this and handle the error.
        No silent fallback; operations fail explicitly.
        """
        if resource_kind not in self.CRITICAL_RESOURCES:
            raise ValueError(f"Unknown resource_kind: {resource_kind}")
        
        try:
            registry = routing_registry()
            route = registry.get_route(
                resource_kind=resource_kind,
                tenant_id=self._context.tenant_id,
                env=self._context.env,
                project_id=self._context.project_id,
            )
            
            if not route:
                raise RuntimeError(
                    f"Route not configured for {resource_kind}. "
                    f"Tenant={self._context.tenant_id}, env={self._context.env}. "
                    f"This operation cannot proceed without a configured route. "
                    f"Configure via /routing/routes with resource_kind={resource_kind}."
                )
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"Failed to check route for {resource_kind}: {e}. "
                f"This operation cannot proceed."
            ) from e


def log_startup_diagnostics(context: RequestContext) -> None:
    """Log startup diagnostics (warning-first).
    
    Call this once at service initialization to surface route issues.
    """
    diag = EnginesDiagnosticsService(context)
    message = diag.get_startup_diagnostics()
    logger.info(message)
