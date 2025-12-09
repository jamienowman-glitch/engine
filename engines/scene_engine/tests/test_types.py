import pytest
from pydantic import ValidationError

from engines.scene_engine.core.types import (
    Box,
    Grid,
    Recipe,
    SceneBuildRequest,
)


def test_scene_build_request_validates_and_defaults() -> None:
    req = SceneBuildRequest(
        grid=Grid(cols=24, rows=1, col_width=1.0, row_height=1.0),
        boxes=[Box(id="box1", x=0, y=0, w=4, h=3, kind="card")],
        recipe=Recipe.wall,
    )
    assert req.grid.cols == 24
    assert req.boxes[0].d == 1.0
    assert req.boxes[0].z == 0.0


def test_scene_build_request_requires_boxes() -> None:
    with pytest.raises(ValidationError):
        SceneBuildRequest(grid=Grid(cols=1, rows=1), boxes=[], recipe=Recipe.wall)
