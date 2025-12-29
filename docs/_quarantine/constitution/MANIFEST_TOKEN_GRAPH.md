# MANIFEST & TOKEN GRAPH CONTRACT

This document defines the canonical manifest shape used by apps/surfaces. It is a contracts-only artifact: no storage or API wiring is defined here.

## Goals
- Single manifest graph per app or surface instance.
- Clear separation of structure (components), content (content_slots), and styling/behaviour (tokens.*).
- Stable path/ID conventions to support scoped patching and capability checks.
- Explicit mapping of atoms/views/sections and the slots/tokens they expose.

## Canonical manifest shape (conceptual)
```json
{
  "manifest_id": "m_123",
  "tenant_id": "t_northstar-dev",
  "env": "dev",
  "surface": "web_home",
  "app_code": "CAIDENCE",
  "version": 3,
  "components": {
    "hero_section": { "type": "section", "atom_id": "hero_section_v1", "slots": ["headline", "body", "cta"], "children": ["hero_view"] },
    "hero_view": { "type": "view", "atom_id": "hero_view_v1", "parent": "hero_section", "children": ["hero_headline", "hero_body", "hero_image"] },
    "hero_headline": { "type": "atom", "atom_id": "headline_v2", "parent": "hero_view" },
    "hero_body": { "type": "atom", "atom_id": "body_v1", "parent": "hero_view" },
    "hero_image": { "type": "atom", "atom_id": "image_v1", "parent": "hero_view" }
  },
  "content_slots": {
    "hero_headline.text": { "kind": "text", "value": "Open up the waters", "locale": "en" },
    "hero_body.text": { "kind": "text", "value": "Swim further, finish fresher." },
    "hero_image.src": { "kind": "image", "value": "https://...", "mime": "image/jpeg" }
  },
  "tokens": {
    "typography": {
      "hero_headline": { "font_id": "roboto_flex", "preset_code": "extrablack", "tracking": 200, "size_px": 64, "line_height": 1.1 },
      "hero_body": { "font_id": "roboto_flex", "preset_code": "regular", "tracking": 0, "size_px": 18 }
    },
    "layout": { "hero_section": { "width": "full", "max_width": "1200px", "padding": "48px 24px", "alignment": "center" } },
    "colour": { "hero_section": { "background": "bg_primary", "foreground": "fg_on_primary", "border": "border_none" } },
    "behaviour": { "hero_section": { "animation": "fade_in", "duration_ms": 400, "easing": "ease-out" } }
  },
  "metadata": { "created_at": "ISO8601", "updated_at": "ISO8601", "origin": { "actor_type": "agent", "actor_id": "ceo" } }
}
```

## Graph entities
- **Surface/manifest root**: unique `manifest_id` per tenant/env/surface/app combination; carries version, metadata, and pointers to component graph.
- **Section**: layout-owning node that can hold nested views and atoms; responsible for top-level tokens such as spacing and colour blocks.
- **View**: mid-level grouping that can sequence atoms and attach domain-specific slots (e.g., a hero view with headline/body/image slots).
- **Atom**: leaf node bound to a library atom_id; atoms expose one or more slots and inherit tokens from their parents unless overridden.
- **Content slot**: typed value bound to a `component.slot` key (e.g., `hero_headline.text`); stores live content only.
- **Token node**: scoped to a domain + component (e.g., `tokens.typography.hero_headline`); stores styling/behaviour only.

## ID and path conventions
- Component IDs are lowercase snake_case, alphanumeric plus underscore; stable and unique per manifest (e.g., `hero_headline`, `footer_cta`).
- Slot names are snake_case and only exist if declared by the component/atom definition.
- `components.<component_id>` contains `{type, atom_id, slots?, parent?, children?}`; parent/children form the manifest tree.
- `content_slots` map keys use `component.slot` (string key), and the addressable patch path is `content_slots.<component_id>.<slot>`.
- Token paths follow `tokens.<domain>.<component_id>.<field>` (e.g., `tokens.typography.hero_headline.tracking`).
- Allowed starter domains: `typography`, `layout`, `colour`, `behaviour`. New domains must follow the same path shape and remain styling/behaviour-only.

## Content slots
- Shape: `{ "kind": "text|rich_text|image|video|url|data_ref", "value": <typed>, "locale?": "en-US", "mime?": "image/jpeg", "source?": "cms|nexus|inline", "ref?": "nexus://..." }`.
- Slots do not carry tokens or styling; they can carry source metadata for traceability.
- Slot values are the live state; drafts or history belong in blackboard/log storage outside the manifest.

## Token domains
Base rules:
- Tokens are per-component overrides; if a component has no entry for a domain, it inherits from its parent or atom defaults.
- Token objects are partial: only supply the fields being overridden; readers must merge with defaults defined by the atom/view library.
- Tokens never include content or URLs.

Typography tokens (`tokens.typography.<component>`):
- Fields: `font_id`, `preset_code`, `tracking`, `size_px`, `line_height`, `letter_case?`, `weight_override?`.
- `font_id` references a registry entry (see PLAN-028); `preset_code` selects the preset; `tracking` in basis points.

Layout tokens (`tokens.layout.<component>`):
- Fields: `width`, `max_width`, `padding`, `margin`, `gap`, `alignment`, `stack_direction`, `z_index?`.
- Values are CSS-like strings or enumerations defined by the layout engine; no raw pixel math in the manifest.

Colour tokens (`tokens.colour.<component>`):
- Fields: `background`, `foreground`, `border`, `accent`, `opacity?`.
- All fields reference palette tokens, not literal hex values.

Behaviour tokens (`tokens.behaviour.<component>`):
- Fields: `animation`, `duration_ms`, `delay_ms?`, `easing`, `interaction?` (e.g., hover/click), `loop?`.
- Behaviour tokens describe orchestration hints only; they do not embed scripts.

## Defaults vs current values
- Manifests carry the current live values. Defaults live in atom/view definitions referenced via `atom_id` or view templates.
- Consumers merge defaults + manifest tokens/content at render time; the manifest itself is the single source of truth for live state.
- `version` increments on applied patch batches; history/blackboard storage is outside this contract.

## Patch addressing rules
- Patch shape: `{ "path": "tokens.typography.hero_headline.tracking", "op": "set|delete|merge", "value?": <typed> }`.
- Addressable families: `components.*`, `content_slots.*`, `tokens.<domain>.*`, `metadata.*`. Cross-family writes are invalid.
- Component creation/removal occurs via `components.<id>`; removing a component also requires cleaning related content slots/tokens in the same patch batch.
- Patches are idempotent and path-scoped; there is no “rebuild view” or bulk overwrite operation.
- Actors carry origin metadata elsewhere (cluster/agent/human) and must stay within their capability-scoped paths.

## Metadata
- `metadata` holds `created_at`, `updated_at`, `origin` (`actor_type`, `actor_id`, `request_id?`), and optional audit hints.
- `app_code`, `surface`, `tenant_id`, and `env` are immutable for the life of a manifest_id.

## Non-goals (this doc)
- No persistence/DB schema.
- No transport or auth rules.
- No model prompts; agents consume the manifest but do not define it here.
