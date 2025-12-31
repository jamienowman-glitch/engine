"""Seed Firestore emulator with minimal routing + identity data for local dev."""
from __future__ import annotations

import os
from uuid import uuid4

from engines.identity.models import (
    App,
    ControlPlaneProject,
    Surface,
    Tenant,
    TenantKeyConfig,
)
from engines.identity.repository import FirestoreIdentityRepository
from engines.routing.manager import REQUIRED_RESOURCE_KINDS
from engines.routing.registry import FirestoreRoutingRegistry, ResourceRoute


TENANT_ID = "t_system"
ENV = os.getenv("ENV", "dev")
PROJECT_ID = "p_system"


def _seed_identity() -> None:
    repo = FirestoreIdentityRepository()
    if not repo.get_tenant(TENANT_ID):
        repo.create_tenant(Tenant(id=TENANT_ID, name="System Control Plane"))

    surfaces = repo.list_surfaces_for_tenant(TENANT_ID)
    surface = surfaces[0] if surfaces else None
    if not surface:
        surface = Surface(tenant_id=TENANT_ID, name="default", description="Dev surface")
        repo.create_surface(surface)

    apps = repo.list_apps_for_tenant(TENANT_ID)
    app = apps[0] if apps else None
    if not app:
        app = App(tenant_id=TENANT_ID, name="default", app_type="web", description="Dev app")
        repo.create_app(app)

    projects = repo.list_projects_for_tenant(TENANT_ID)
    if not any(p.id == PROJECT_ID and p.env == ENV for p in projects):
        repo.create_project(
            ControlPlaneProject(
                tenant_id=TENANT_ID,
                env=ENV,
                project_id=PROJECT_ID,
                name="Dev Project",
                description="Local dev project",
                default_surface_id=surface.id,
                default_app_id=app.id,
            )
        )

    # Auth signing slot (repo lookup will fall back to env, but we store it for parity)
    if not repo.get_key_config(TENANT_ID, "prod", "auth_jwt_signing"):
        repo.set_key_config(
            TenantKeyConfig(
                tenant_id=TENANT_ID,
                env="prod",
                slot="auth_jwt_signing",
                provider="local",
                secret_name="AUTH_JWT_SIGNING",
            )
        )


def _route_backend_for_kind(kind: str) -> tuple[str, dict]:
    filesystem = {"root": os.path.join(os.path.expanduser("~"), ".northstar", kind)}
    mapping = {
        "budget": ("filesystem", {"root": os.getenv("BUDGET_BACKEND_FS_DIR", filesystem["root"])}),
        "raw_storage": ("filesystem", {"root": filesystem["root"]}),
        "media_v2_storage": ("filesystem", {"root": filesystem["root"]}),
        "chat_bus": ("redis", {"host": os.getenv("REDIS_HOST", "localhost"), "port": os.getenv("REDIS_PORT", "6379")}),
        "timeline": ("firestore", {}),
    }
    backend, config = mapping.get(kind, ("firestore", {}))
    return backend, config


def _seed_routing() -> None:
    registry = FirestoreRoutingRegistry()
    for kind in REQUIRED_RESOURCE_KINDS:
        backend, config = _route_backend_for_kind(kind)
        route = ResourceRoute(
            id=f"{kind}-{TENANT_ID}-{ENV}",
            resource_kind=kind,
            tenant_id=TENANT_ID,
            env=ENV,
            project_id=None,
            backend_type=backend,
            config=config,
            required=True,
        )
        registry.upsert_route(route)


def main() -> None:
    if not os.getenv("FIRESTORE_EMULATOR_HOST"):
        raise SystemExit("FIRESTORE_EMULATOR_HOST must point at the emulator (e.g., localhost:8900)")
    _seed_identity()
    _seed_routing()
    print("Seeded Firestore emulator for dev-local.")


if __name__ == "__main__":
    main()
