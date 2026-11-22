"""Block ray tracing and interaction target selection."""
from __future__ import annotations

from dataclasses import dataclass
import math

from engine.core import BlockPos, EnumFacing, Vec3d
from engine.blocks import BLOCK_REGISTRY


@dataclass(frozen=True)
class BlockRayHit:
    pos: BlockPos
    block: object
    side_hit: EnumFacing | None
    hit_vector: Vec3d
    distance: float


class InteractionManager:
    """Voxel DDA ray tracer for selecting collidable blocks."""

    def __init__(self, world) -> None:
        self.world = world

    def ray_trace_blocks(self, start: Vec3d, direction: Vec3d,
                         max_distance: float = 5.0) -> BlockRayHit | None:
        if not isinstance(start, Vec3d) or not isinstance(direction, Vec3d):
            raise TypeError("start and direction must be Vec3d values")
        if (isinstance(max_distance, bool) or not isinstance(max_distance, (int, float))
                or not math.isfinite(max_distance) or max_distance < 0):
            raise ValueError("max_distance must be a finite non-negative number")
        if not all(math.isfinite(v) for v in (start.x, start.y, start.z,
                                               direction.x, direction.y, direction.z)):
            raise ValueError("ray coordinates must be finite")

        ray = direction.normalize()
        if ray.length_squared() == 0:
            return None

        x, y, z = math.floor(start.x), math.floor(start.y), math.floor(start.z)
        start_pos = BlockPos(x, y, z)
        initial_id = self.world.get_block_state_id(start_pos)
        initial_block = BLOCK_REGISTRY.by_id(initial_id)
        if initial_block is not None and initial_block.can_collide():
            return BlockRayHit(start_pos, initial_block, None, start, 0.0)

        def axis_values(origin: float, cell: int, delta: float):
            if delta > 0:
                return 1, (cell + 1 - origin) / delta, 1.0 / delta
            if delta < 0:
                return -1, (cell - origin) / delta, -1.0 / delta
            return 0, math.inf, math.inf

        step_x, max_x, delta_x = axis_values(start.x, x, ray.x)
        step_y, max_y, delta_y = axis_values(start.y, y, ray.y)
        step_z, max_z, delta_z = axis_values(start.z, z, ray.z)

        while True:
            if max_x <= max_y and max_x <= max_z:
                distance = max_x
                if distance > max_distance:
                    return None
                x += step_x
                max_x += delta_x
                face = EnumFacing.WEST if step_x > 0 else EnumFacing.EAST
            elif max_y <= max_z:
                distance = max_y
                if distance > max_distance:
                    return None
                y += step_y
                max_y += delta_y
                face = EnumFacing.DOWN if step_y > 0 else EnumFacing.UP
            else:
                distance = max_z
                if distance > max_distance:
                    return None
                z += step_z
                max_z += delta_z
                face = EnumFacing.NORTH if step_z > 0 else EnumFacing.SOUTH

            pos = BlockPos(x, y, z)
            block_id = self.world.get_block_state_id(pos)
            block = BLOCK_REGISTRY.by_id(block_id)
            if block is not None and block.can_collide():
                hit = Vec3d(
                    start.x + ray.x * distance,
                    start.y + ray.y * distance,
                    start.z + ray.z * distance,
                )
                return BlockRayHit(pos, block, face, hit, distance)


__all__ = ["InteractionManager", "BlockRayHit"]
