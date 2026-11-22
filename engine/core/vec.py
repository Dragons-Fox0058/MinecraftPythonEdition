"""engine.core.vec — Vec3d and Vec3i (Minecraft 1.12.2 double/int vectors)."""

from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass(frozen=True, slots=True)
class Vec3d:
    x: float
    y: float
    z: float

    def __add__(self, o): return Vec3d(self.x + o.x, self.y + o.y, self.z + o.z)
    def __sub__(self, o): return Vec3d(self.x - o.x, self.y - o.y, self.z - o.z)
    def __mul__(self, s): return Vec3d(self.x * s, self.y * s, self.z * s)
    __rmul__ = __mul__

    def dot(self, o): return self.x*o.x + self.y*o.y + self.z*o.z
    def cross(self, o):
        return Vec3d(self.y*o.z - self.z*o.y,
                     self.z*o.x - self.x*o.z,
                     self.x*o.y - self.y*o.x)

    def length_squared(self): return self.dot(self)
    def length(self): return math.sqrt(self.length_squared())
    def distance_to(self, o): return (self - o).length()
    def normalize(self):
        L = self.length()
        return Vec3d(0.0, 0.0, 0.0) if L < 1e-4 else Vec3d(self.x/L, self.y/L, self.z/L)

    def scale(self, s): return Vec3d(self.x*s, self.y*s, self.z*s)
    def add_vector(self, x, y, z): return Vec3d(self.x+x, self.y+y, self.z+z)

    def to_block_pos(self):
        from engine.core.blockpos import BlockPos
        return BlockPos(int(math.floor(self.x)), int(math.floor(self.y)), int(math.floor(self.z)))

    def __repr__(self):
        return f'Vec3d({self.x:.4f}, {self.y:.4f}, {self.z:.4f})'

@dataclass(frozen=True, slots=True)
class Vec3i:
    x: int
    y: int
    z: int

    def __add__(self, o): return Vec3i(self.x + o.x, self.y + o.y, self.z + o.z)
    def __sub__(self, o): return Vec3i(self.x - o.x, self.y - o.y, self.z - o.z)
    def dot(self, o): return self.x*o.x + self.y*o.y + self.z*o.z
    def cross(self, o):
        return Vec3i(self.y*o.z - self.z*o.y,
                     self.z*o.x - self.x*o.z,
                     self.x*o.y - self.y*o.x)
    def length_squared(self): return self.dot(self)
    def distance_sq(self, o): return (self - o).length_squared()
