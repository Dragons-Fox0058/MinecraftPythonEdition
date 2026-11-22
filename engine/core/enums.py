"""engine.core.enums — Minecraft 1.12.2 EnumFacing and related enums."""

from __future__ import annotations
from enum import IntEnum

class EnumFacing(IntEnum):
    """Minecraft EnumFacing. Index order matches 1.12.2 (DOWN..EAST)."""
    DOWN  = 0
    UP    = 1
    NORTH = 2
    SOUTH = 3
    WEST  = 4
    EAST  = 5

    @property
    def opposite(self) -> "EnumFacing":
        return _OPPOSITE[self]

    @property
    def axis(self) -> str:
        return _AXIS[self]

    @property
    def axis_direction(self) -> int:
        return _AXIS_DIR[self]

    @property
    def offset(self) -> tuple[int, int, int]:
        return _OFFSET[self]

    @property
    def horizontal_index(self) -> int:
        return _HORIZONTAL_INDEX[self]

    def rotate_y(self) -> "EnumFacing":
        return _ROTATE_Y[self]

    @property
    def is_horizontal(self) -> bool:
        return self.axis != 'Y'

    @property
    def is_vertical(self) -> bool:
        return self.axis == 'Y'

_OPPOSITE = {
    EnumFacing.DOWN:  EnumFacing.UP,
    EnumFacing.UP:    EnumFacing.DOWN,
    EnumFacing.NORTH: EnumFacing.SOUTH,
    EnumFacing.SOUTH: EnumFacing.NORTH,
    EnumFacing.WEST:  EnumFacing.EAST,
    EnumFacing.EAST:  EnumFacing.WEST,
}

_AXIS = {
    EnumFacing.DOWN:  'Y', EnumFacing.UP:   'Y',
    EnumFacing.NORTH: 'Z', EnumFacing.SOUTH:'Z',
    EnumFacing.WEST:  'X', EnumFacing.EAST: 'X',
}

_AXIS_DIR = {
    EnumFacing.DOWN:  -1, EnumFacing.UP:    1,
    EnumFacing.NORTH: -1, EnumFacing.SOUTH: 1,
    EnumFacing.WEST:  -1, EnumFacing.EAST:  1,
}

_OFFSET = {
    EnumFacing.DOWN:  (0, -1, 0),
    EnumFacing.UP:    (0, 1, 0),
    EnumFacing.NORTH: (0, 0, -1),
    EnumFacing.SOUTH: (0, 0, 1),
    EnumFacing.WEST:  (-1, 0, 0),
    EnumFacing.EAST:  (1, 0, 0),
}

_HORIZONTAL_INDEX = {
    EnumFacing.NORTH: 0, EnumFacing.EAST: 1,
    EnumFacing.SOUTH: 2, EnumFacing.WEST: 3,
}

_ROTATE_Y = {
    EnumFacing.NORTH: EnumFacing.EAST,
    EnumFacing.EAST:  EnumFacing.SOUTH,
    EnumFacing.SOUTH: EnumFacing.WEST,
    EnumFacing.WEST:  EnumFacing.NORTH,
    EnumFacing.UP:    EnumFacing.UP,
    EnumFacing.DOWN:  EnumFacing.DOWN,
}

HORIZONTALS = (EnumFacing.NORTH, EnumFacing.EAST, EnumFacing.SOUTH, EnumFacing.WEST)

def by_2d_data(data: int) -> "EnumFacing":
    """Map 0..3 (S,W,N,E in 1.12.2) to horizontal EnumFacing."""
    table = (EnumFacing.SOUTH, EnumFacing.WEST, EnumFacing.NORTH, EnumFacing.EAST)
    return table[data & 3]
