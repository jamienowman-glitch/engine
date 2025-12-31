#!/usr/bin/env python3
"""
Seeds data for local development:
1. Routes in FilesystemRoutingRegistry
2. Identity entities in MemoryIdentityRepository
"""
import sys
import os
import uuid
from typing import Optional

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ensure env matches
os.environ["ROUTING_REGISTRY_BACKEND"] = "filesystem"
os.environ["IDENTITY_BACKEND"] = "memory"

from engines.routing.registry import routing_registry, ResourceRoute
from engines.identity.state import identity_repo
from engines.identity.models import Tenant, User, TenantMembership, ControlPlaneProject, TenantMode, Surface, App

REQUIRED_RESOURCE_KINDS = [
    "feature_flags", "strategy_lock", "kpi", "budget", "maybes",
    "memory", "analytics_events", "rate_limit", "firearms",
    "page_content", "seo", "realtime_registry", "chat_bus",
    "nexus_backend", "media_v2_storage", "raw_storage", "timeline",
]

def seed_routing():
    print("Seeding local routing registry...")
    registry = routing_registry()
    tenant_id = "t_system"
    env = "dev"
    
    for kind in REQUIRED_RESOURCE_KINDS:
        existing = registry.get_route(kind, tenant_id, env)
        if not existing:
            route = ResourceRoute(
                id=str(uuid.uuid4()),
                resource_kind=kind,
                tenant_id=tenant_id,
                env=env,
                backend_type="filesystem", 
                config={"root": ".northstar/data"},
                required=True
            )
            registry.upsert_route(route)

def seed_identity():
    print("Seeding memory identity repo...")
    if not identity_repo.get_tenant("t_system"):
        identity_repo.create_tenant(Tenant(id="t_system", name="System Tenant", status="active"))

    if not identity_repo.get_user("dev-user-001"):
        identity_repo.create_user(User(id="dev-user-001", email="dev@local.test"))

    if not identity_repo.find_membership("t_system", "dev-user-001"):
         identity_repo.create_membership(TenantMembership(
             tenant_id="t_system", user_id="dev-user-001", role="owner", status="active"
         ))

    for mode in ["saas", "lab", "enterprise"]:
        if not identity_repo.get_tenant_mode_by_name(mode):
             identity_repo.create_tenant_mode(TenantMode(name=mode))

    if not identity_repo.get_surface("s_default"):
        print("  Creating surface s_default...")
        identity_repo.create_surface(Surface(id="s_default", tenant_id="t_system", name="Default Surface"))

    if not identity_repo.get_app("a_default"):
        print("  Creating app a_default...")
        identity_repo.create_app(App(id="a_default", tenant_id="t_system", name="Default App"))

    if not identity_repo.get_project("t_system", "dev", "p_default"):
         print("  Creating project p_default...")
         identity_repo.create_project(ControlPlaneProject(
             tenant_id="t_system", env="dev", project_id="p_default", name="Default Project",
             default_surface_id="s_default",
             default_app_id="a_default"
         ))

def main():
    seed_routing()
    seed_identity()
    print("Seeding complete.")

if __name__ == "__main__":
    main()
