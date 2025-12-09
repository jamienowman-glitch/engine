"""Vector Explorer recipe: use embedded vector metadata for placement."""
from __future__ import annotations

from typing import List

from engines.scene_engine.core.types import Box, Grid, GridBox3D, SceneNode, WorldPosition


def _vector_to_position(box: Box) -> WorldPosition | None:
    vector = box.meta.get("vector") if isinstance(box.meta, dict) else None
    if isinstance(vector, (list, tuple)) and len(vector) >= 3:
        try:
            x, y, z = float(vector[0]), float(vector[1]), float(vector[2])
            return WorldPosition(x=x, y=y, z=z)
        except (TypeError, ValueError):
            return None
    return None


def render_vector_explorer(grid: Grid, boxes: List[Box]) -> List[SceneNode]:
    nodes: List[SceneNode] = []
    origin_x = grid.cols / 2.0
    origin_y = grid.rows / 2.0
    for box in boxes:
        vec_pos = _vector_to_position(box)
        if vec_pos is not None:
            world_pos = vec_pos
        else:
            world_pos = WorldPosition(
                x=(box.x + box.w / 2.0 - origin_x) * grid.col_width,
                y=(box.y + box.h / 2.0 - origin_y) * grid.row_height,
                z=box.z,
            )
        nodes.append(
            SceneNode(
                id=box.id,
                kind=box.kind,
                gridBox3D=GridBox3D(x=box.x, y=box.y, z=box.z, w=box.w, h=box.h, d=box.d),
                worldPosition=world_pos,
                meta=box.meta,
            )
        )
    return nodes
