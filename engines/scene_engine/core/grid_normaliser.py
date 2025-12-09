"""Grid and box normalisation engine (SE-01.C)."""
from __future__ import annotations

from typing import List, Tuple

from engines.scene_engine.core.types import Box, Grid


class GridNormalisationError(ValueError):
    """Raised when grid or box data is invalid."""


def normalise(grid: Grid, boxes: List[Box]) -> Tuple[Grid, List[Box]]:
    if grid.cols <= 0 or grid.rows <= 0:
        raise GridNormalisationError("grid dimensions must be positive")
    normalised: List[Box] = []
    for box in boxes:
        # Pydantic already coerces numbers; enforce positivity for sizes.
        if box.w <= 0 or box.h <= 0 or box.d <= 0:
            raise GridNormalisationError(f"invalid dimensions for box {box.id}")
        normalised.append(
            Box(
                id=box.id,
                x=float(box.x),
                y=float(box.y),
                z=float(box.z if box.z is not None else 0.0),
                w=float(box.w),
                h=float(box.h),
                d=float(box.d if box.d is not None else 1.0),
                kind=box.kind,
                meta=box.meta,
            )
        )
    if not normalised:
        raise GridNormalisationError("at least one box is required")
    return grid, normalised
