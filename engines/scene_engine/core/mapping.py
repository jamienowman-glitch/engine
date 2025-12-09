"""Grid to world mapping and recipe dispatcher (SE-01.D)."""
from __future__ import annotations

from typing import List

from engines.scene_engine.core.grid_normaliser import normalise
from engines.scene_engine.core.recipes.vector_explorer import render_vector_explorer
from engines.scene_engine.core.recipes.wall import render_wall
from engines.scene_engine.core.types import Box, Grid, Recipe, SceneNode


def map_boxes(grid: Grid, boxes: List[Box], recipe: Recipe) -> List[SceneNode]:
    _grid, norm_boxes = normalise(grid, boxes)
    if recipe == Recipe.wall:
        return render_wall(_grid, norm_boxes)
    if recipe in (Recipe.vector_explorer, Recipe.vector_space_explorer):
        return render_vector_explorer(_grid, norm_boxes)
    raise ValueError(f"Unsupported recipe: {recipe}")
