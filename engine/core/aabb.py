"""engine.core.aabb — AxisAlignedBB matching 1.12.2 semantics."""

from __future__ import annotations
from dataclasses import dataclass
from engine.core.vec import Vec3d
from engine.core.blockpos import BlockPos

@dataclass(frozen=True, slots=True)
class AxisAlignedBB:
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float

    @staticmethod
    def from_block(pos: BlockPos) -> "AxisAlignedBB":
        return AxisAlignedBB(pos.x, pos.y, pos.z,
                             pos.x + 1.0, pos.y + 1.0, pos.z + 1.0)

    @staticmethod
    def of(min_x, min_y, min_z, max_x, max_y, max_z) -> "AxisAlignedBB":
        return AxisAlignedBB(min_x, min_y, min_z, max_x, max_y, max_z)

    def expand(self, x, y, z) -> "AxisAlignedBB":
        """Symmetrically expand (or shrink for negative values)."""
        return AxisAlignedBB(
            self.min_x - x, self.min_y - y, self.min_z - z,
            self.max_x + x, self.max_y + y, self.max_z + z
        )

    def add_coord(self, x, y, z) -> "AxisAlignedBB":
        """Extend only in the direction of movement."""
        return AxisAlignedBB(
            self.min_x + min(x, 0), 
            self.min_y + min(y, 0),
            self.min_z + min(z, 0),
            self.max_x + max(x, 0),
            self.max_y + max(y, 0),
            self.max_z + max(z, 0)
        )

    def grow(self, v) -> "AxisAlignedBB":
        if isinstance(v, (int, float)):
            return self.expand(v, v, v)
        return self.expand(v.x, v.y, v.z)

    def offset(self, x, y, z) -> "AxisAlignedBB":
        return AxisAlignedBB(self.min_x + x, self.min_y + y, self.min_z + z,
                             self.max_x + x, self.max_y + y, self.max_z + z)

    def intersects(self, o: "AxisAlignedBB") -> bool:
        return (self.min_x < o.max_x and self.max_x > o.min_x
            and self.min_y < o.max_y and self.max_y > o.min_y
            and self.min_z < o.max_z and self.max_z > o.min_z)

    def contains(self, v: Vec3d) -> bool:
        return (self.min_x <= v.x < self.max_x
            and self.min_y <= v.y < self.max_y
            and self.min_z <= v.z < self.max_z)

    def calculate_x_offset(self, o, offset: float) -> float:
        # Vanilla AxisAlignedBB.calculateXOffset
        if o.max_y <= self.min_y or o.min_y >= self.max_y: return offset
        if o.max_z <= self.min_z or o.min_z >= self.max_z: return offset
        if offset > 0 and o.max_x <= self.min_x:
            d0 = self.min_x - o.max_x
            if d0 < offset: offset = d0
        if offset < 0 and o.min_x >= self.max_x:
            d1 = self.max_x - o.min_x
            if d1 > offset: offset = d1
        return offset

    def calculate_y_offset(self, o, offset: float) -> float:
        # self is the obstacle; o is the moving box.
        if o.max_x <= self.min_x or o.min_x >= self.max_x:
            return offset
        if o.max_z <= self.min_z or o.min_z >= self.max_z:
            return offset

        # Moving upward: obstacle is above the moving box.
        if offset > 0 and o.max_y <= self.min_y:
            d0 = self.min_y - o.max_y
            if d0 < offset:
                offset = d0

        # Moving downward: obstacle is below the moving box.
        if offset < 0 and o.min_y >= self.max_y:
            d1 = self.max_y - o.min_y
            if d1 > offset:
                offset = d1

        return offset

    def calculate_z_offset(self, o, offset: float) -> float:
        # Vanilla AxisAlignedBB.calculateZOffset
        if o.max_x <= self.min_x or o.min_x >= self.max_x: return offset
        if o.max_y <= self.min_y or o.min_y >= self.max_y: return offset
        if offset > 0 and o.max_z <= self.min_z:
            d0 = self.min_z - o.max_z
            if d0 < offset: offset = d0
        if offset < 0 and o.min_z >= self.max_z:
            d1 = self.max_z - o.min_z
            if d1 > offset: offset = d1
        return offset

    def contract(self, x, y, z) -> "AxisAlignedBB":
        return self.expand(-x, -y, -z)

    def get_center(self) -> Vec3d:
        return Vec3d((self.min_x + self.max_x) * 0.5,
                     (self.min_y + self.max_y) * 0.5,
                     (self.min_z + self.max_z) * 0.5)
