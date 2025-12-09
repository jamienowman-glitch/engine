# VECTOR EXPLORER → SCENE MAPPING (PLAN-0AI-P2)

Recipe name: `vector_space_explorer` (alias of existing vector_explorer).

Mapping `VectorExplorerItem` → Scene Engine `Box`:
- `id` → `box.id`
- `label` → `meta.title`
- `tags` → `meta.tags`
- `metrics` → `meta.metrics`
- `similarity_score` → `meta.similarity_score`
- `source_ref` → `meta.source_ref`
- `vector_ref` (if present) → `meta.vector_ref`
- `height_score` (optional scalar for UI height) → `meta.height_score`
- `cluster_id` (optional grouping/affinity key) → `meta.cluster_id`

Layout:
- Grid auto-generated as near-square: `cols = ceil(sqrt(n))`, `rows = ceil(n / cols)`, `col_width = row_height = 1.0`.
- Boxes placed row-wise with `w=h=1.0`, `x=row index`, `y=col index`, `z=0`.
- Vector coordinates in `meta.vector` (if provided) override grid placement inside the vector_explorer renderer.

Scene build:
- Build `SceneBuildRequest` with `recipe="vector_space_explorer"`, `grid` as above, `boxes` derived from items, then dispatch through Scene Engine mapper.

Logging:
- DatasetEvents emitted: `vector_explorer.query` (input filters/mode), `vector_explorer.scene_composed` (includes item ids/count and trace_id).
