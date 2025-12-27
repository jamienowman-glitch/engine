"""Repository interfaces for identity/tenant records."""
from __future__ import annotations

from typing import Dict, Optional, Protocol

from engines.identity.models import Tenant, TenantAnalyticsConfig, TenantKeyConfig, TenantMembership, User, TenantMode, Surface, App, ControlPlaneProject


class IdentityRepository(Protocol):
    """Storage abstraction for identity backbone."""

    def create_user(self, user: User) -> User: ...
    def get_user(self, user_id: str) -> Optional[User]: ...
    def get_user_by_email(self, email: str) -> Optional[User]: ...
    def list_users_for_tenant(self, tenant_id: str) -> list[User]: ...

    def create_tenant(self, tenant: Tenant) -> Tenant: ...
    def get_tenant(self, tenant_id: str) -> Optional[Tenant]: ...
    def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]: ...
    def list_tenants_for_user(self, user_id: str) -> list[Tenant]: ...

    def create_membership(self, membership: TenantMembership) -> TenantMembership: ...
    def get_membership(self, membership_id: str) -> Optional[TenantMembership]: ...
    def find_membership(self, tenant_id: str, user_id: str) -> Optional[TenantMembership]: ...
    def list_memberships_for_user(self, user_id: str) -> list[TenantMembership]: ...
    def list_memberships_for_tenant(self, tenant_id: str) -> list[TenantMembership]: ...

    def set_key_config(self, config: TenantKeyConfig) -> TenantKeyConfig: ...
    def get_key_config(self, tenant_id: str, env: str, slot: str) -> Optional[TenantKeyConfig]: ...
    def list_key_configs(self, tenant_id: str) -> list[TenantKeyConfig]: ...
    def upsert_analytics_config(self, config: TenantAnalyticsConfig) -> TenantAnalyticsConfig: ...
    def list_analytics_configs(self, tenant_id: str, env: Optional[str] = None, surface: Optional[str] = None) -> list[TenantAnalyticsConfig]: ...
    def get_analytics_config(self, tenant_id: str, env: str, surface: str) -> Optional[TenantAnalyticsConfig]: ...
    
    def create_tenant_mode(self, mode: TenantMode) -> TenantMode: ...
    def get_tenant_mode(self, mode_id: str) -> Optional[TenantMode]: ...
    def get_tenant_mode_by_name(self, name: str) -> Optional[TenantMode]: ...
    def list_tenant_modes(self) -> list[TenantMode]: ...
    
    # Control-plane primitives (Phase 0 closeout)
    def create_surface(self, surface: Surface) -> Surface: ...
    def get_surface(self, surface_id: str) -> Optional[Surface]: ...
    def list_surfaces_for_tenant(self, tenant_id: str) -> list[Surface]: ...
    def update_surface(self, surface_id: str, **kwargs) -> Optional[Surface]: ...
    
    def create_app(self, app: App) -> App: ...
    def get_app(self, app_id: str) -> Optional[App]: ...
    def list_apps_for_tenant(self, tenant_id: str) -> list[App]: ...
    def update_app(self, app_id: str, **kwargs) -> Optional[App]: ...
    
    def create_project(self, project: ControlPlaneProject) -> ControlPlaneProject: ...
    def get_project(self, tenant_id: str, env: str, project_id: str) -> Optional[ControlPlaneProject]: ...
    def list_projects_for_tenant(self, tenant_id: str, env: Optional[str] = None) -> list[ControlPlaneProject]: ...
    def update_project(self, tenant_id: str, env: str, project_id: str, **kwargs) -> Optional[ControlPlaneProject]: ...


class InMemoryIdentityRepository:
    """In-memory implementation for dev/tests; swap with Firestore later."""

    def __init__(self) -> None:
        self._users: Dict[str, User] = {}
        self._tenants: Dict[str, Tenant] = {}
        self._memberships: Dict[str, TenantMembership] = {}
        self._keys: Dict[tuple[str, str, str], TenantKeyConfig] = {}
        self._analytics: Dict[tuple[str, str, str], TenantAnalyticsConfig] = {}
        self._tenant_modes: Dict[str, TenantMode] = {}
        self._surfaces: Dict[str, Surface] = {}
        self._apps: Dict[str, App] = {}
        self._projects: Dict[tuple[str, str, str], ControlPlaneProject] = {}  # (tenant_id, env, project_id)


    # Users
    def create_user(self, user: User) -> User:
        self._users[user.id] = user
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        for u in self._users.values():
            if u.email.lower() == email.lower():
                return u
        return None

    def list_users_for_tenant(self, tenant_id: str) -> list[User]:
        member_user_ids = {m.user_id for m in self._memberships.values() if m.tenant_id == tenant_id}
        return [u for u in self._users.values() if u.id in member_user_ids]

    # Tenants
    def create_tenant(self, tenant: Tenant) -> Tenant:
        self._tenants[tenant.id] = tenant
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        return self._tenants.get(tenant_id)

    def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        for t in self._tenants.values():
            if t.slug and t.slug == slug:
                return t
        return None

    def list_tenants_for_user(self, user_id: str) -> list[Tenant]:
        tenant_ids = {m.tenant_id for m in self._memberships.values() if m.user_id == user_id}
        return [t for t in self._tenants.values() if t.id in tenant_ids]

    # Memberships
    def create_membership(self, membership: TenantMembership) -> TenantMembership:
        self._memberships[membership.id] = membership
        return membership

    def get_membership(self, membership_id: str) -> Optional[TenantMembership]:
        return self._memberships.get(membership_id)

    def find_membership(self, tenant_id: str, user_id: str) -> Optional[TenantMembership]:
        for m in self._memberships.values():
            if m.tenant_id == tenant_id and m.user_id == user_id:
                return m
        return None

    def list_memberships_for_user(self, user_id: str) -> list[TenantMembership]:
        return [m for m in self._memberships.values() if m.user_id == user_id]

    def list_memberships_for_tenant(self, tenant_id: str) -> list[TenantMembership]:
        return [m for m in self._memberships.values() if m.tenant_id == tenant_id]

    # Key configs
    def set_key_config(self, config: TenantKeyConfig) -> TenantKeyConfig:
        key = (config.tenant_id, config.env, config.slot)
        self._keys[key] = config
        return config

    def get_key_config(self, tenant_id: str, env: str, slot: str) -> Optional[TenantKeyConfig]:
        return self._keys.get((tenant_id, env, slot))

    def list_key_configs(self, tenant_id: str) -> list[TenantKeyConfig]:
        return [cfg for (t, _, _), cfg in self._keys.items() if t == tenant_id]

    # Analytics configs
    def upsert_analytics_config(self, config: TenantAnalyticsConfig) -> TenantAnalyticsConfig:
        key = (config.tenant_id, config.env, config.surface)
        self._analytics[key] = config
        return config

    def list_analytics_configs(self, tenant_id: str, env: Optional[str] = None, surface: Optional[str] = None) -> list[TenantAnalyticsConfig]:
        results = [cfg for (t, _, _), cfg in self._analytics.items() if t == tenant_id]
        if env:
            results = [c for c in results if c.env == env]
        if surface:
            results = [c for c in results if c.surface == surface]
        return results

    def get_analytics_config(self, tenant_id: str, env: str, surface: str) -> Optional[TenantAnalyticsConfig]:
        return self._analytics.get((tenant_id, env, surface))

    # Tenant Modes
    def create_tenant_mode(self, mode: TenantMode) -> TenantMode:
        self._tenant_modes[mode.id] = mode
        return mode

    def get_tenant_mode(self, mode_id: str) -> Optional[TenantMode]:
        return self._tenant_modes.get(mode_id)

    def get_tenant_mode_by_name(self, name: str) -> Optional[TenantMode]:
        for mode in self._tenant_modes.values():
            if mode.name == name:
                return mode
        return None

    def list_tenant_modes(self) -> list[TenantMode]:
        return list(self._tenant_modes.values())
    
    # Control-plane primitives (Phase 0 closeout)
    def create_surface(self, surface: Surface) -> Surface:
        self._surfaces[surface.id] = surface
        return surface

    def get_surface(self, surface_id: str) -> Optional[Surface]:
        return self._surfaces.get(surface_id)

    def list_surfaces_for_tenant(self, tenant_id: str) -> list[Surface]:
        return [s for s in self._surfaces.values() if s.tenant_id == tenant_id]

    def update_surface(self, surface_id: str, **kwargs) -> Optional[Surface]:
        surface = self._surfaces.get(surface_id)
        if not surface:
            return None
        for key, value in kwargs.items():
            if hasattr(surface, key):
                setattr(surface, key, value)
        return surface
    
    def create_app(self, app: App) -> App:
        self._apps[app.id] = app
        return app

    def get_app(self, app_id: str) -> Optional[App]:
        return self._apps.get(app_id)

    def list_apps_for_tenant(self, tenant_id: str) -> list[App]:
        return [a for a in self._apps.values() if a.tenant_id == tenant_id]

    def update_app(self, app_id: str, **kwargs) -> Optional[App]:
        app = self._apps.get(app_id)
        if not app:
            return None
        for key, value in kwargs.items():
            if hasattr(app, key):
                setattr(app, key, value)
        return app
    
    def create_project(self, project: ControlPlaneProject) -> ControlPlaneProject:
        key = (project.tenant_id, project.env, project.project_id)
        self._projects[key] = project
        return project

    def get_project(self, tenant_id: str, env: str, project_id: str) -> Optional[ControlPlaneProject]:
        return self._projects.get((tenant_id, env, project_id))

    def list_projects_for_tenant(self, tenant_id: str, env: Optional[str] = None) -> list[ControlPlaneProject]:
        projects = [p for p in self._projects.values() if p.tenant_id == tenant_id]
        if env:
            projects = [p for p in projects if p.env == env]
        return projects

    def update_project(self, tenant_id: str, env: str, project_id: str, **kwargs) -> Optional[ControlPlaneProject]:
        key = (tenant_id, env, project_id)
        project = self._projects.get(key)
        if not project:
            return None
        for key_name, value in kwargs.items():
            if hasattr(project, key_name):
                setattr(project, key_name, value)
        return project


class FirestoreIdentityRepository:
    """Firestore-backed identity repository.

    Collections:
    - identity_users/{user_id}
    - identity_tenants/{tenant_id}
    - identity_memberships/{membership_id}
    - key_configs/{tenant_env_slot}
    - analytics_configs/{tenant_env_surface}
    - tenant_modes/{mode_id}
    """


    def __init__(self, client: Optional[object] = None) -> None:
        try:
            from google.cloud import firestore  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dep
            raise RuntimeError("google-cloud-firestore not installed") from exc
        from engines.config import runtime_config

        project = runtime_config.get_firestore_project()
        if not project:
            raise RuntimeError("GCP project is required for Firestore identity repo")
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]
        self._col_users = "identity_users"
        self._col_tenants = "identity_tenants"
        self._col_memberships = "identity_memberships"
        self._col_keys = "key_configs"
        self._col_analytics = "analytics_configs"
        self._col_tenant_modes = "tenant_modes"
        self._col_surfaces = "control_plane_surfaces"
        self._col_apps = "control_plane_apps"
        self._col_projects = "control_plane_projects"


    def _col(self, name: str):
        return self._client.collection(name)

    # Users
    def create_user(self, user: User) -> User:
        self._col(self._col_users).document(user.id).set(user.model_dump())
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        snap = self._col(self._col_users).document(user_id).get()
        return User(**snap.to_dict()) if snap and snap.exists else None

    def get_user_by_email(self, email: str) -> Optional[User]:
        docs = self._col(self._col_users).where("email", "==", email).limit(1).stream()
        for d in docs:
            return User(**d.to_dict())
        return None

    def list_users_for_tenant(self, tenant_id: str) -> list[User]:
        membership_docs = (
            self._col(self._col_memberships)
            .where("tenant_id", "==", tenant_id)
            .where("status", "==", "active")
            .stream()
        )
        user_ids = [d.to_dict()["user_id"] for d in membership_docs]
        if not user_ids:
            return []
        users: list[User] = []
        for uid in user_ids:
            snap = self._col(self._col_users).document(uid).get()
            if snap and snap.exists:
                users.append(User(**snap.to_dict()))
        return users

    # Tenants
    def create_tenant(self, tenant: Tenant) -> Tenant:
        self._col(self._col_tenants).document(tenant.id).set(tenant.model_dump())
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        snap = self._col(self._col_tenants).document(tenant_id).get()
        return Tenant(**snap.to_dict()) if snap and snap.exists else None

    def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        docs = self._col(self._col_tenants).where("slug", "==", slug).limit(1).stream()
        for d in docs:
            return Tenant(**d.to_dict())
        return None

    def list_tenants_for_user(self, user_id: str) -> list[Tenant]:
        memberships = (
            self._col(self._col_memberships)
            .where("user_id", "==", user_id)
            .where("status", "==", "active")
            .stream()
        )
        tenant_ids = [m.to_dict()["tenant_id"] for m in memberships]
        if not tenant_ids:
            return []
        results: list[Tenant] = []
        for tid in tenant_ids:
            snap = self._col(self._col_tenants).document(tid).get()
            if snap and snap.exists:
                results.append(Tenant(**snap.to_dict()))
        return results

    # Memberships
    def create_membership(self, membership: TenantMembership) -> TenantMembership:
        self._col(self._col_memberships).document(membership.id).set(membership.model_dump())
        return membership

    def get_membership(self, membership_id: str) -> Optional[TenantMembership]:
        snap = self._col(self._col_memberships).document(membership_id).get()
        return TenantMembership(**snap.to_dict()) if snap and snap.exists else None

    def find_membership(self, tenant_id: str, user_id: str) -> Optional[TenantMembership]:
        docs = (
            self._col(self._col_memberships)
            .where("tenant_id", "==", tenant_id)
            .where("user_id", "==", user_id)
            .limit(1)
            .stream()
        )
        for d in docs:
            return TenantMembership(**d.to_dict())
        return None

    def list_memberships_for_user(self, user_id: str) -> list[TenantMembership]:
        docs = self._col(self._col_memberships).where("user_id", "==", user_id).stream()
        return [TenantMembership(**d.to_dict()) for d in docs]

    def list_memberships_for_tenant(self, tenant_id: str) -> list[TenantMembership]:
        docs = self._col(self._col_memberships).where("tenant_id", "==", tenant_id).stream()
        return [TenantMembership(**d.to_dict()) for d in docs]

    # Key configs
    def set_key_config(self, config: TenantKeyConfig) -> TenantKeyConfig:
        self._col(self._col_keys).document(f"{config.tenant_id}_{config.env}_{config.slot}").set(config.model_dump())
        return config

    def get_key_config(self, tenant_id: str, env: str, slot: str) -> Optional[TenantKeyConfig]:
        snap = self._col(self._col_keys).document(f"{tenant_id}_{env}_{slot}").get()
        return TenantKeyConfig(**snap.to_dict()) if snap and snap.exists else None

    def list_key_configs(self, tenant_id: str) -> list[TenantKeyConfig]:
        docs = self._col(self._col_keys).where("tenant_id", "==", tenant_id).stream()
        return [TenantKeyConfig(**d.to_dict()) for d in docs]

    # Analytics configs
    def upsert_analytics_config(self, config: TenantAnalyticsConfig) -> TenantAnalyticsConfig:
        self._col(self._col_analytics).document(f"{config.tenant_id}_{config.env}_{config.surface}").set(config.model_dump())
        return config

    def list_analytics_configs(self, tenant_id: str, env: Optional[str] = None, surface: Optional[str] = None) -> list[TenantAnalyticsConfig]:
        query = self._col(self._col_analytics).where("tenant_id", "==", tenant_id)
        if env:
            query = query.where("env", "==", env)
        if surface:
            query = query.where("surface", "==", surface)
        docs = query.stream()
        return [TenantAnalyticsConfig(**d.to_dict()) for d in docs]

    def get_analytics_config(self, tenant_id: str, env: str, surface: str) -> Optional[TenantAnalyticsConfig]:
        snap = self._col(self._col_analytics).document(f"{tenant_id}_{env}_{surface}").get()
        return TenantAnalyticsConfig(**snap.to_dict()) if snap and snap.exists else None
    # Tenant Modes
    def create_tenant_mode(self, mode: TenantMode) -> TenantMode:
        self._col(self._col_tenant_modes).document(mode.id).set(mode.model_dump())
        return mode

    def get_tenant_mode(self, mode_id: str) -> Optional[TenantMode]:
        snap = self._col(self._col_tenant_modes).document(mode_id).get()
        return TenantMode(**snap.to_dict()) if snap and snap.exists else None

    def get_tenant_mode_by_name(self, name: str) -> Optional[TenantMode]:
        docs = self._col(self._col_tenant_modes).where("name", "==", name).limit(1).stream()
        for d in docs:
            return TenantMode(**d.to_dict())
        return None

    def list_tenant_modes(self) -> list[TenantMode]:
        docs = self._col(self._col_tenant_modes).stream()
        return [TenantMode(**d.to_dict()) for d in docs]
    
    # Control-plane primitives (Phase 0 closeout)
    def create_surface(self, surface: Surface) -> Surface:
        self._col(self._col_surfaces).document(surface.id).set(surface.model_dump())
        return surface

    def get_surface(self, surface_id: str) -> Optional[Surface]:
        snap = self._col(self._col_surfaces).document(surface_id).get()
        return Surface(**snap.to_dict()) if snap and snap.exists else None

    def list_surfaces_for_tenant(self, tenant_id: str) -> list[Surface]:
        docs = self._col(self._col_surfaces).where("tenant_id", "==", tenant_id).stream()
        return [Surface(**d.to_dict()) for d in docs]

    def update_surface(self, surface_id: str, **kwargs) -> Optional[Surface]:
        snap = self._col(self._col_surfaces).document(surface_id).get()
        if not snap or not snap.exists:
            return None
        data = snap.to_dict()
        data.update(kwargs)
        self._col(self._col_surfaces).document(surface_id).set(data)
        return Surface(**data)
    
    def create_app(self, app: App) -> App:
        self._col(self._col_apps).document(app.id).set(app.model_dump())
        return app

    def get_app(self, app_id: str) -> Optional[App]:
        snap = self._col(self._col_apps).document(app_id).get()
        return App(**snap.to_dict()) if snap and snap.exists else None

    def list_apps_for_tenant(self, tenant_id: str) -> list[App]:
        docs = self._col(self._col_apps).where("tenant_id", "==", tenant_id).stream()
        return [App(**d.to_dict()) for d in docs]

    def update_app(self, app_id: str, **kwargs) -> Optional[App]:
        snap = self._col(self._col_apps).document(app_id).get()
        if not snap or not snap.exists:
            return None
        data = snap.to_dict()
        data.update(kwargs)
        self._col(self._col_apps).document(app_id).set(data)
        return App(**data)
    
    def create_project(self, project: ControlPlaneProject) -> ControlPlaneProject:
        doc_id = f"{project.tenant_id}_{project.env}_{project.project_id}"
        self._col(self._col_projects).document(doc_id).set(project.model_dump())
        return project

    def get_project(self, tenant_id: str, env: str, project_id: str) -> Optional[ControlPlaneProject]:
        doc_id = f"{tenant_id}_{env}_{project_id}"
        snap = self._col(self._col_projects).document(doc_id).get()
        return ControlPlaneProject(**snap.to_dict()) if snap and snap.exists else None

    def list_projects_for_tenant(self, tenant_id: str, env: Optional[str] = None) -> list[ControlPlaneProject]:
        query = self._col(self._col_projects).where("tenant_id", "==", tenant_id)
        if env:
            query = query.where("env", "==", env)
        docs = query.stream()
        return [ControlPlaneProject(**d.to_dict()) for d in docs]

    def update_project(self, tenant_id: str, env: str, project_id: str, **kwargs) -> Optional[ControlPlaneProject]:
        doc_id = f"{tenant_id}_{env}_{project_id}"
        snap = self._col(self._col_projects).document(doc_id).get()
        if not snap or not snap.exists:
            return None
        data = snap.to_dict()
        data.update(kwargs)
        self._col(self._col_projects).document(doc_id).set(data)
        return ControlPlaneProject(**data)