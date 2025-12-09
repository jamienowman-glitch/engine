import pytest

from engines.scene_engine.core.mapping import map_boxes
from engines.scene_engine.core.types import Box, Grid, Recipe


def test_map_boxes_wall_returns_nodes() -> None:
    grid = Grid(cols=4, rows=1)
    boxes = [Box(id="b1", x=0, y=0, w=2, h=1, kind="card")]
    nodes = map_boxes(grid, boxes, Recipe.wall)
    assert len(nodes) == 1
    assert nodes[0].worldPosition.z == 0.0


def test_map_boxes_vector_explorer_defaults_to_grid_position() -> None:
    grid = Grid(cols=4, rows=1)
    boxes = [Box(id="b1", x=1, y=0, w=1, h=1, kind="point")]
    nodes = map_boxes(grid, boxes, Recipe.vector_explorer)
    assert len(nodes) == 1
    assert nodes[0].worldPosition.x != 0  # centered mapping applied


def test_map_boxes_rejects_unknown_recipe() -> None:
    grid = Grid(cols=4, rows=1)
    boxes = [Box(id="b1", x=0, y=0, w=1, h=1, kind="card")]
    with pytest.raises(ValueError):
        map_boxes(grid, boxes, "unknown")  # type: ignore[arg-type]
