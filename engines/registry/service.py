from __future__ import annotations

import base64
import binascii
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from engines.common.error_envelope import cursor_invalid_error, error_response
from engines.common.identity import RequestContext
from engines.registry.repository import ComponentRegistryRepository

SpecKind = Literal["atom", "component", "lens", "graphlens", "canvas"]


class ComponentSpec(BaseModel):
    """Lightweight descriptor for a registered component."""

    id: str
    version: int
    schema: Optional[Dict[str, Any]] = None
    defaults: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class AtomSpec(BaseModel):
    """Definition of a registered atom with token surfaces."""

    id: str
    version: int
    schema: Optional[Dict[str, Any]] = None
    defaults: Optional[Dict[str, Any]] = None
    token_surface: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class ComponentsPayload(BaseModel):
    """Response payload for /registry/components."""

    version: int
    components: List[ComponentSpec]


class AtomsPayload(BaseModel):
    """Response payload for /registry/atoms."""

    version: int
    atoms: List[AtomSpec]


class RegistrySpec(BaseModel):
    """Full descriptor for a registry spec."""

    id: str
    kind: SpecKind
    version: int
    schema: Dict[str, Any]
    defaults: Dict[str, Any]
    controls: Dict[str, Any]
    token_surface: List[str]
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class RegistrySpecsPayload(BaseModel):
    """Response for /registry/specs listings."""

    specs: List[RegistrySpec]
    next_cursor: Optional[str] = None
    version: int = 0
    etag: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class ComponentRegistryService:
    """Service exposing registry snapshots with deterministic ordering."""

    SPEC_KINDS = {"atom", "component", "lens", "graphlens", "canvas"}
    SPEC_PAGE_SIZE = 50

    def __init__(self, repo: Optional[ComponentRegistryRepository] = None) -> None:
        self.repo = repo or ComponentRegistryRepository()

    def get_components(self, ctx: RequestContext) -> ComponentsPayload:
        raw_components = self.repo.list_components(ctx)
        components = [
            ComponentSpec.model_validate(record)
            for record in raw_components
        ]
        components.sort(key=lambda comp: comp.id)
        highest_version = max((comp.version for comp in components), default=0)
        return ComponentsPayload(version=highest_version, components=components)

    def get_atoms(self, ctx: RequestContext) -> AtomsPayload:
        raw_atoms = self.repo.list_atoms(ctx)
        atoms: List[AtomSpec] = []
        for record in raw_atoms:
            try:
                spec = AtomSpec.model_validate(record)
            except ValidationError as exc:
                error_response(
                    code="component_registry.invalid_atom_spec",
                    message="Invalid AtomSpec stored in registry",
                    status_code=400,
                    resource_kind="component_registry",
                    details={
                        "errors": exc.errors(),
                        "entry": record.get("id"),
                    },
                )
            atoms.append(spec)
        atoms.sort(key=lambda atom: atom.id)
        highest_version = max((atom.version for atom in atoms), default=0)
        return AtomsPayload(version=highest_version, atoms=atoms)

    def list_specs(
        self,
        ctx: RequestContext,
        kind: str,
        cursor: Optional[str] = None,
    ) -> RegistrySpecsPayload:
        normalized_kind = (kind or "").lower()
        if normalized_kind not in self.SPEC_KINDS:
            error_response(
                code="component_registry.invalid_spec_kind",
                message=f"Unsupported spec kind: {kind}",
                status_code=400,
                resource_kind="component_registry",
                details={"kind": kind},
            )

        offset = 0
        if cursor:
            try:
                offset = self._decode_cursor(cursor)
            except ValueError:
                cursor_invalid_error(
                    cursor,
                    domain="component_registry",
                    resource_kind="component_registry",
                )

        raw_specs = self.repo.list_specs(ctx)
        specs: List[RegistrySpec] = []
        for record in raw_specs:
            if str(record.get("kind", "")).lower() != normalized_kind:
                continue
            try:
                spec = RegistrySpec.model_validate(record)
            except ValidationError as exc:
                error_response(
                    code="component_registry.invalid_spec",
                    message="Invalid spec stored in registry",
                    status_code=400,
                    resource_kind="component_registry",
                    details={
                        "errors": exc.errors(),
                        "entry": record.get("id"),
                    },
                )
            specs.append(spec)

        specs.sort(key=lambda spec: spec.id)

        if offset > len(specs):
            cursor_invalid_error(
                cursor or "",
                domain="component_registry",
                resource_kind="component_registry",
            )

        page = specs[offset : offset + self.SPEC_PAGE_SIZE]
        next_cursor = None
        if offset + len(page) < len(specs):
            next_cursor = self._encode_cursor(offset + len(page))

        highest_version = max((spec.version for spec in specs), default=0)
        return RegistrySpecsPayload(
            specs=page,
            next_cursor=next_cursor,
            version=highest_version,
        )

    def get_spec(self, ctx: RequestContext, spec_id: str) -> Optional[RegistrySpec]:
        record = self.repo.get_spec(ctx, spec_id)
        if not record:
            return None
        try:
            return RegistrySpec.model_validate(record)
        except ValidationError as exc:
            error_response(
                code="component_registry.invalid_spec",
                message="Invalid spec stored in registry",
                status_code=400,
                resource_kind="component_registry",
                details={
                    "errors": exc.errors(),
                    "entry": spec_id,
                },
            )

    def save_component(self, ctx: RequestContext, component: Dict[str, Any]) -> None:
        """Helper for tests or admin tooling to persist components."""
        self.repo.save_component(ctx, component)

    def save_atom(self, ctx: RequestContext, atom: Dict[str, Any]) -> None:
        """Helper for tests or admin tooling to persist atoms."""
        self.repo.save_atom(ctx, atom)

    def save_spec(self, ctx: RequestContext, spec: Dict[str, Any]) -> None:
        """Helper for tests or admin tooling to persist specs."""
        self.repo.save_spec(ctx, spec)

    @staticmethod
    def _encode_cursor(offset: int) -> str:
        token = str(offset).encode("ascii")
        return base64.urlsafe_b64encode(token).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str) -> int:
        trimmed = cursor.strip()
        padded = trimmed + "=" * (-len(trimmed) % 4)
        try:
            decoded = base64.urlsafe_b64decode(padded).decode("ascii")
            offset = int(decoded)
        except (ValueError, binascii.Error):
            raise ValueError("Invalid cursor")
        if offset < 0:
            raise ValueError("Invalid cursor")
        return offset


_default_service: Optional[ComponentRegistryService] = None


def get_component_registry_service() -> ComponentRegistryService:
    global _default_service
    if _default_service is None:
        _default_service = ComponentRegistryService()
    return _default_service


def set_component_registry_service(service: ComponentRegistryService) -> None:
    global _default_service
    _default_service = service
