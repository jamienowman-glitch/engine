"""Wall recipe: place boxes on a flat wall at z=0."""
from __future__ import annotations

from typing import List

from engines.scene_engine.core.types import Box, Grid, GridBox3D, SceneNode, WorldPosition


def render_wall(grid: Grid, boxes: List[Box]) -> List[SceneNode]:
    nodes: List[SceneNode] = []
    origin_x = grid.cols / 2.0
    origin_y = grid.rows / 2.0
    for box in boxes:
        world_x = (box.x + box.w / 2.0 - origin_x) * grid.col_width
        world_y = (box.y + box.h / 2.0 - origin_y) * grid.row_height
        world_z = 0.0
        nodes.append(
            SceneNode(
                id=box.id,
                kind=box.kind,
                gridBox3D=GridBox3D(x=box.x, y=box.y, z=0.0, w=box.w, h=box.h, d=box.d),
                worldPosition=WorldPosition(x=world_x, y=world_y, z=world_z),
                meta=box.meta,
            )
        )
    return nodes
