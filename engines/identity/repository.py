"""Repository interfaces for identity/tenant records."""
from __future__ import annotations

from typing import Dict, Optional, Protocol

from engines.identity.models import Tenant, TenantAnalyticsConfig, TenantKeyConfig, TenantMembership, User


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


class InMemoryIdentityRepository:
    """In-memory implementation for dev/tests; swap with Firestore later."""

    def __init__(self) -> None:
        self._users: Dict[str, User] = {}
        self._tenants: Dict[str, Tenant] = {}
        self._memberships: Dict[str, TenantMembership] = {}
        self._keys: Dict[tuple[str, str, str], TenantKeyConfig] = {}
        self._analytics: Dict[tuple[str, str, str], TenantAnalyticsConfig] = {}

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


class FirestoreIdentityRepository:
    """Firestore-backed identity repository.

    Collections:
    - identity_users/{user_id}
    - identity_tenants/{tenant_id}
    - identity_memberships/{membership_id}
    - key_configs/{tenant_env_slot}
    - analytics_configs/{tenant_env_surface}
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
