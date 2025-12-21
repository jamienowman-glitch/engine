"""Data models for Environment Kit & Layout Engine (P0)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from engines.scene_engine.core.geometry import Vector3


class EnvPrimitiveKind(str, Enum):
    FLOOR = "FLOOR"
    CEILING = "CEILING"
    WALL_SEGMENT = "WALL_SEGMENT"
    DOOR_OPENING = "DOOR_OPENING"
    WINDOW_OPENING = "WINDOW_OPENING"
    COLUMN = "COLUMN"
    STAIRS_SIMPLE = "STAIRS_SIMPLE"
    ROOT_ROOM = "ROOT_ROOM"


class RoomParams(BaseModel):
    width: float
    depth: float
    height: float
    wall_thickness: float = 0.2
    with_ceiling: bool = True
    origin: Vector3 = Field(default_factory=lambda: Vector3(x=0, y=0, z=0))


class WallSegmentParams(BaseModel):
    length: float
    height: float
    thickness: float
    origin: Vector3  # base position in world
    direction: Vector3  # normalized horizontal direction along the wall


class OpeningParams(BaseModel):
    width: float
    height: float
    sill_height: float  # distance from floor
    offset_along_wall: float  # distance from wall start
