# Fonts Helper & Registry

Contract PLAN-028 now describes the runtime registry used by typography/image/video engines. The JSON files under `engines/design/fonts/` model every font, its axis presets, and envelope/clamp rules so backend renderers can stay deterministic.

## Runtime schema
```json
{
  "font_id": "roboto_flex",
  "display_name": "Roboto Flex",
  "css_family_name": "\"Roboto Flex\", system-ui, -apple-system, sans-serif",
  "tracking_min_design": -200,
  "tracking_max_design": 200,
  "tracking_default_design": 0,
  "primary_file_path": "fonts/roboto-flex/RobotoFlex-VariableFont.ttf",
  "axes": {
    "opsz": { "min": 8, "max": 144, "default": 14 },
    "wght": { "min": 100, "max": 1000, "default": 400 },
    "GRAD": { "min": -200, "max": 200, "default": 0 },
    "wdth": { "min": 50, "max": 151, "default": 100 }
  },
  "presets": {
    "regular": { "opsz": 14, "wght": 400, "GRAD": 0, "wdth": 100 },
    "extrablack": { "opsz": 14, "wght": 1000, "GRAD": 0, "wdth": 100 }
  }
}
```

- `font_id` is the lookup key; `display_name`/`font_id` are both valid handles at runtime.
- `axes` lists every supported axis with `min`, `max`, and `default` so callers can clamp overrides before passing them to layout.
- `presets` provide starting axis values; the registry merges any `axis_overrides` with the preset before building variation strings.
- Every font JSON sits next to the actual `.ttf`/`.otf` under `engines/design/fonts/`, so renderers can resolve disk paths without guessing.

## Helper behaviour
1. Accept `{ font_id, preset_code, tracking?, axis_overrides? }`.
2. Lookup the font; if missing, raise `unknown_font`.
3. Lookup the preset; if missing, fall back to the first preset available (to stay resilient when new fonts only expose a single instance).
4. Clamp `tracking` to `[tracking_min_design, tracking_max_design]` and convert to an em-based letter spacing that downstream renderers reuse.
5. Merge the preset axes with overrides and clamp every axis to its built-in bounds so renderers never ask for out-of-range values.
6. Emit tokens plus axis metadata:
```json
{
  "fontFamily": "\"Roboto Flex\", system-ui, -apple-system, sans-serif",
  "fontVariationSettings": "'GRAD' 0, 'opsz' 14, 'wdth' 100, 'wght' 400",
  "letterSpacing": "-0.0500em",
  "variant_axes": { "wght": 400, "wdth": 100, "opsz": 14, "GRAD": 0 }
}
```
- Helper is deterministic: same inputs always produce the same tokens, axis map, and letter spacing.

## Tests
- Unknown font raises `KeyError`.
- Preset fallback is predictable (first preset returned when requested code is missing).
- Tracking clamps to `tracking_min_design`/`tracking_max_design`.
- Axis overrides clamp per-axis and appear in the emitted metadata.
