# Fonts Helper & Registry

Planning-only contract for font registry + helper (PLAN-028). Defines schemas and clamping rules; no runtime code in this pass.

## Inputs from cards/apps
- Cards pass `font_id`, `preset_code`, and optional `tracking` adjustment (design units basis points).
- Cards never pass raw axis values.

## Font config schema (registry entry)
```json
{
  "font_id": "roboto_flex",
  "display_name": "Roboto Flex",
  "css_family_name": "'Roboto Flex', sans-serif",
  "tracking_bounds": { "min": -50, "max": 300 },
  "axes": {
    "wght": { "min": 100, "max": 1000 },
    "wdth": { "min": 75, "max": 125 }
  },
  "presets": {
    "regular": { "wght": 400, "wdth": 100, "opsz": 16 },
    "extrablack": { "wght": 1000, "wdth": 100, "opsz": 48 }
  }
}
```
- `font_id` is the lookup key; `presets` map codes to axis values; `tracking_bounds` used to clamp card-provided tracking.
- Registry stored as JSON under `docs/engines/fonts/` (planned); helper loads into memory.

## Helper behaviour
1) Accept input `{ font_id, preset_code, tracking? }`.
2) Lookup font; if missing, raise `unknown_font`.
3) Lookup preset; if missing, raise `unknown_preset`.
4) Clamp `tracking` to `[min, max]` bounds; default tracking = 0 if omitted.
5) Emit tokens:
```json
{
  "fontFamily": "'Roboto Flex', sans-serif",
  "fontVariationSettings": "'wght' 400, 'wdth' 100, 'opsz' 16",
  "letterSpacing": "0.12em"  // based on clamped tracking
}
```
- Helper is deterministic: same inputs → same tokens; ignores unknown axes in presets.

## Tests (future)
- Unknown font/preset throws.
- Tracking clamps to min/max.
- Stable token generation for known font/preset combos.
- Supports Roboto Flex as initial registry entry; extendable with more fonts using same shape.

## Consumers
- UI/engines consume emitted tokens; framework-agnostic (usable in React/Tailwind/static).
- Cards/apps should cache `font_id` + `preset_code` + `tracking` combinations; server can recompute tokens consistently.
