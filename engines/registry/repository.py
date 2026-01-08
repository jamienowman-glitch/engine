from __future__ import annotations

from typing import Any, Dict, List, Optional

from engines.common.error_envelope import missing_route_error
from engines.common.identity import RequestContext
from engines.storage.routing_service import TabularStoreService


class ComponentRegistryRepository:
    """Routing-aware persistence for component/atom/lens registry snapshots."""

    COMPONENTS_TABLE = "component_registry_components"
    ATOMS_TABLE = "component_registry_atoms"
    SPECS_TABLE = "component_registry_specs"

    def _tabular(self, ctx: RequestContext) -> TabularStoreService:
        try:
            return TabularStoreService(ctx, resource_kind="component_registry")
        except RuntimeError as exc:
            raise missing_route_error(
                resource_kind="component_registry",
                tenant_id=ctx.tenant_id,
                env=ctx.env,
            ) from exc

    def list_components(self, ctx: RequestContext) -> List[Dict[str, Any]]:
        """Return all component records for the current context."""
        return self._tabular(ctx).list_by_prefix(self.COMPONENTS_TABLE, "", ctx)

    def list_atoms(self, ctx: RequestContext) -> List[Dict[str, Any]]:
        """Return all atom records for the current context."""
        return self._tabular(ctx).list_by_prefix(self.ATOMS_TABLE, "", ctx)

    def list_specs(self, ctx: RequestContext) -> List[Dict[str, Any]]:
        """Return all registered specs for the current context."""
        return self._tabular(ctx).list_by_prefix(self.SPECS_TABLE, "", ctx)

    def get_spec(self, ctx: RequestContext, spec_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single spec by ID."""
        return self._tabular(ctx).get(self.SPECS_TABLE, spec_id, ctx)

    def save_component(self, ctx: RequestContext, component: Dict[str, Any]) -> None:
        """Persist a component record (tests/admin helpers only)."""
        component_id = component.get("id")
        if not component_id:
            raise ValueError("component data must include id")
        self._tabular(ctx).upsert(self.COMPONENTS_TABLE, component_id, component, ctx)

    def save_atom(self, ctx: RequestContext, atom: Dict[str, Any]) -> None:
        """Persist an atom record (tests/admin helpers only)."""
        atom_id = atom.get("id")
        if not atom_id:
            raise ValueError("atom data must include id")
        self._tabular(ctx).upsert(self.ATOMS_TABLE, atom_id, atom, ctx)

    def save_spec(self, ctx: RequestContext, spec: Dict[str, Any]) -> None:
        """Persist a spec record (tests/admin helpers only)."""
        spec_id = spec.get("id")
        if not spec_id:
            raise ValueError("spec data must include id")
        self._tabular(ctx).upsert(self.SPECS_TABLE, spec_id, spec, ctx)
