from engines.scene_engine.core.recipes.vector_explorer import render_vector_explorer
from engines.scene_engine.core.recipes.wall import render_wall
from engines.scene_engine.core.types import Box, Grid


def test_wall_places_on_z_zero() -> None:
    grid = Grid(cols=4, rows=1)
    nodes = render_wall(grid, [Box(id="b1", x=0, y=0, w=1, h=1, kind="card")])
    assert nodes[0].worldPosition.z == 0.0


def test_vector_explorer_uses_vector_meta_when_available() -> None:
    grid = Grid(cols=4, rows=1)
    box = Box(id="b1", x=0, y=0, w=1, h=1, kind="point", meta={"vector": [1, 2, 3]})
    nodes = render_vector_explorer(grid, [box])
    assert nodes[0].worldPosition.x == 1.0
    assert nodes[0].worldPosition.y == 2.0
    assert nodes[0].worldPosition.z == 3.0
