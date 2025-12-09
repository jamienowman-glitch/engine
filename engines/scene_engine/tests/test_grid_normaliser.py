import pytest

from engines.scene_engine.core.grid_normaliser import GridNormalisationError, normalise
from engines.scene_engine.core.types import Box, Grid


def test_normalise_defaults_and_validation() -> None:
    grid = Grid(cols=24, rows=1)
    boxes = [Box(id="b1", x=0, y=0, w=4, h=3, kind="card")]
    g, norm_boxes = normalise(grid, boxes)
    assert g.cols == 24
    assert norm_boxes[0].z == 0.0
    assert norm_boxes[0].d == 1.0


def test_normalise_rejects_bad_dimensions() -> None:
    grid = Grid(cols=24, rows=1)
    with pytest.raises(GridNormalisationError):
        normalise(grid, [Box(id="b1", x=0, y=0, w=0.1, h=0, kind="card")])


def test_normalise_requires_boxes() -> None:
    grid = Grid(cols=24, rows=1)
    with pytest.raises(GridNormalisationError):
        normalise(grid, [])
