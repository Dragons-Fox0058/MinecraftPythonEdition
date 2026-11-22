"""Block breaking progress and harvesting decisions."""
from __future__ import annotations

from dataclasses import dataclass
import math

from engine.blocks import BLOCK_REGISTRY
from engine.core import BlockPos


@dataclass(frozen=True)
class BlockBreakResult:
    pos: BlockPos
    block_id: int
    block_name: str
    broken: bool
    harvested: bool
    progress: float


class BlockBreaking:
    """Tracks vanilla-style relative block damage for one active target.

    Tool effectiveness and harvest requirements are supplied by the caller
    until the tool/item catalogue is implemented.
    """

    def __init__(self, world) -> None:
        self.world = world
        self.target: BlockPos | None = None
        self.progress = 0.0

    @staticmethod
    def relative_hardness(hardness: float, dig_speed: float = 1.0,
                          can_harvest: bool = False) -> float:
        if not math.isfinite(hardness) or not math.isfinite(dig_speed):
            raise ValueError("hardness and dig_speed must be finite")
        if dig_speed < 0:
            raise ValueError("dig_speed cannot be negative")
        if hardness < 0 or dig_speed == 0:
            return 0.0
        if hardness == 0:
            return 1.0
        divisor = 30.0 if can_harvest else 100.0
        return dig_speed / hardness / divisor

    def reset(self) -> None:
        self.target = None
        self.progress = 0.0

    def damage_block(self, pos: BlockPos, dig_speed: float = 1.0,
                     can_harvest: bool = False) -> BlockBreakResult:
        if not isinstance(pos, BlockPos):
            raise TypeError("pos must be a BlockPos")
        block_id = self.world.get_block_state_id(pos)
        block = BLOCK_REGISTRY.by_id(block_id)
        if block is None or block_id == 0:
            self.reset()
            return BlockBreakResult(pos, block_id, "air", False, False, 0.0)

        if self.target != pos:
            self.target = pos
            self.progress = 0.0

        increment = self.relative_hardness(block.hardness, dig_speed, can_harvest)
        self.progress = min(1.0, self.progress + increment)
        if self.progress < 1.0:
            return BlockBreakResult(
                pos, block_id, block.registry_name, False, False, self.progress
            )

        # The world API currently stores block IDs, so this removes the block
        # without pretending that block drops or tile-entity handling exist.
        self.world.set_block_state_id(pos, 0)
        result = BlockBreakResult(
            pos, block_id, block.registry_name, True, bool(can_harvest), 1.0
        )
        self.reset()
        return result


__all__ = ["BlockBreaking", "BlockBreakResult"]
