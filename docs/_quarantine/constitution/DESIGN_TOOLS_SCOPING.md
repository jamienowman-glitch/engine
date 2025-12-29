# DESIGN TOOLS SCOPING (TYPOGRAPHY / LAYOUT / COLOUR / COPY)

Specialisation of the manifest + capability model for creative tools (slides/canvas/video strips). Planning/contracts only; no runtime wiring.

## Representing layers/slides/clips (examples)

Slide/frame:
```json
"components": {
  "slide_1": { "type": "slide", "children": ["layer_bg", "layer_text"] },
  "layer_text": { "type": "text_layer", "parent": "slide_1", "slots": ["text"] }
},
"content_slots": {
  "layer_text.text": { "kind": "text", "value": "Open up the waters" }
},
"tokens": {
  "typography": { "layer_text": { "font_id": "roboto_flex", "preset_code": "extrablack", "tracking": 200 } },
  "layout": { "layer_text": { "x": 100, "y": 200, "width": 400, "height": 120, "z": 3 } },
  "colour": { "layer_text": { "fill": "fg_primary", "stroke": "none" } }
}
```

Video strip:
```json
"components": { "clip_1": { "type": "clip", "track": 1 } },
"content_slots": { "clip_1.src": { "kind": "video", "value": "gs://..." } },
"tokens": { "timeline": { "clip_1": { "start_ms": 0, "end_ms": 8000 } }, "layout": { "clip_1": { "x": 0, "y": 0, "width": 1920, "height": 1080 } } }
```

Same manifest pattern; only token domains differ.

## Tool-family clusters (design intent)
- Typography cluster: `allowed_writes = ["tokens.typography.*"]`; `allowed_reads = ["content_slots.*", "tokens.*"]`.
- Layout cluster: `allowed_writes = ["tokens.layout.*", "tokens.timeline.*"]`; may read `components.*` for hierarchy and snap rules.
- Colour grading cluster: `allowed_writes = ["tokens.colour.*"]`; may read `content_slots.*` for palette inference but cannot modify them.
- Copywriting cluster: `allowed_writes = ["content_slots.*text", "content_slots.*caption"]`; `allowed_reads` may include typography/layout for context.
- Media cluster: `allowed_writes = ["content_slots.*src"]` when adding/replacing assets; cannot alter typography/layout.

Enforcement principle:
- Typography cluster cannot change `content_slots.*`.
- Copy cluster cannot change `tokens.typography.*`.
- All enforcement flows through the capability + patch rules defined in PLAN-0AB.

## Interaction model hints (no code)
- Moving an element: UI sends layout token patches (e.g., `tokens.layout.layer_text.x`).
- “Make this headline louder”: agent/cluster adjusts `tokens.typography.*` (wght/opsz/tracking), not the text content.
- Reactive changes from events should still emit scoped patches, not freeform regeneration.
- Slides/layers support pinning/locking: locked layers block writes except by authorised clusters; represented as `metadata.locked=true` (out of scope for runtime here).
- Timeline edits: adjust `tokens.timeline.<clip>.start_ms/end_ms`; avoid recreating clips when trimming.
- Colour adjustments: prefer palette token refs over raw RGBA; gradients represented as tokens, not content.

## Non-goals (this doc)
- No UI, transport, or connector/model choices.
- No pricing/LLM selection; those live in cards/OS.
