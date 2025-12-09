"""Map vector explorer items into a Scene Engine request."""
from __future__ import annotations

import math
from typing import Iterable, List

from engines.scene_engine.core.mapping import map_boxes
from engines.scene_engine.core.types import Box, Grid, Recipe, Scene
from engines.nexus.vector_explorer.schemas import VectorExplorerItem


def build_scene(items: Iterable[VectorExplorerItem]) -> Scene:
    items_list = list(items)
    if not items_list:
        return Scene(nodes=[])
    cols = math.ceil(math.sqrt(len(items_list)))
    rows = math.ceil(len(items_list) / cols)
    grid = Grid(cols=cols, rows=rows, col_width=1.0, row_height=1.0)
    boxes: List[Box] = []
    for idx, item in enumerate(items_list):
        x = idx % cols
        y = idx // cols
        meta = {
            "title": item.label,
            "tags": item.tags,
            "metrics": item.metrics,
            "similarity_score": item.similarity_score,
            "source_ref": item.source_ref,
            "height_score": item.height_score,
            "cluster_id": item.cluster_id,
        }
        if item.vector_ref:
            meta["vector_ref"] = item.vector_ref
        boxes.append(
            Box(
                id=item.id,
                x=float(x),
                y=float(y),
                z=0.0,
                w=1.0,
                h=1.0,
                d=1.0,
                kind="vector_item",
                meta=meta,
            )
        )
    nodes = map_boxes(grid, boxes, Recipe.vector_space_explorer)
    return Scene(nodes=nodes)
