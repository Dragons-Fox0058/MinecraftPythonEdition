"""engine.core.blockpos — BlockPos and ChunkPos for 1.12.2 coordinates."""

from __future__ import annotations
from dataclasses import dataclass

# 1.12.2 coordinate limits: x,z fit in 26 bits signed (about +-3.3e7),
# y is 0..255. But BlockPos in vanilla is a full int triple. We keep the
# full int for forward compatibility and enforce y-range only at the world layer.
MIN_BUILD_HEIGHT = 0
MAX_BUILD_HEIGHT = 255
CHUNK_SIZE = 16
CHUNK_HEIGHT = 256
CHUNK_MASK = 15

@dataclass(frozen=True, slots=True)
class BlockPos:
    x: int
    y: int
    z: int

    def offset(self, face_or_dx, dy=None, dz=None):
        from engine.core.enums import EnumFacing
        if isinstance(face_or_dx, EnumFacing):
            dx, dyv, dzv = face_or_dx.offset
            return BlockPos(self.x + dx, self.y + dyv, self.z + dzv)
        return BlockPos(self.x + face_or_dx, self.y + dy, self.z + dz)

    def up(self, n=1): return BlockPos(self.x, self.y + n, self.z)
    def down(self, n=1): return BlockPos(self.x, self.y - n, self.z)
    def north(self, n=1): return BlockPos(self.x, self.y, self.z - n)
    def south(self, n=1): return BlockPos(self.x, self.y, self.z + n)
    def west(self, n=1): return BlockPos(self.x - n, self.y, self.z)
    def east(self, n=1): return BlockPos(self.x + n, self.y, self.z)

    @property
    def chunk_x(self): return self.x >> 4
    @property
    def chunk_z(self): return self.z >> 4

    def to_chunk_pos(self): return ChunkPos(self.chunk_x, self.chunk_z)

    def to_immutable(self): return self

    def as_tuple(self): return (self.x, self.y, self.z)

    def __add__(self, o): return BlockPos(self.x+o.x, self.y+o.y, self.z+o.z)
    def __sub__(self, o): return BlockPos(self.x-o.x, self.y-o.y, self.z-o.z)

@dataclass(frozen=True, slots=True)
class ChunkPos:
    x: int
    z: int

    @property
    def start_x(self): return self.x << 4
    @property
    def start_z(self): return self.z << 4

    def as_long(self) -> int:
        # Same packing as 1.12.2 ChunkPos.asLong
        return (self.x & 0xFFFFFFFF) | ((self.z & 0xFFFFFFFF) << 32)

    @staticmethod
    def from_long(v: int) -> "ChunkPos":
        x = v & 0xFFFFFFFF
        if x >= 0x80000000: x -= 0x100000000
        z = (v >> 32) & 0xFFFFFFFF
        if z >= 0x80000000: z -= 0x100000000
        return ChunkPos(x, z)
