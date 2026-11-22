"""Block breaking progress, harvesting decisions, and optional loot drops."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable

from engine.blocks import BLOCK_REGISTRY
from engine.core import BlockPos
from engine.gameplay.drops import ItemDropManager
from engine.gameplay.items import ItemStack


@dataclass(frozen=True)
class BlockBreakResult:
    pos: BlockPos
    block_id: int
    block_name: str
    broken: bool
    can_harvest: bool
    progress: float
    drops: tuple[ItemStack, ...] = ()


class BlockBreaking:
    """Tracks vanilla-style relative block damage for one active target.

    Tool effectiveness, harvest requirements, and the loot table are supplied
    by the caller until the complete 1.12.2 item/block catalogue is verified.
    """

    def __init__(self, world, drop_resolver: Callable | None = None) -> None:
        if drop_resolver is not None and not callable(drop_resolver):
            raise TypeError("drop_resolver must be callable")
        self.world = world
        self.drop_resolver = drop_resolver
        self.drop_manager = ItemDropManager(world)
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

    def _resolve_drops(self, block, pos: BlockPos, can_harvest: bool) -> tuple[ItemStack, ...]:
        if not can_harvest or self.drop_resolver is None:
            return ()
        rules = getattr(self.world, "game_rules", None)
        if rules is not None and not rules.get_bool("doTileDrops"):
            return ()
        resolved = self.drop_resolver(block, pos)
        if resolved is None:
            return ()
        spawned: list[ItemStack] = []
        for stack in resolved:
            if not isinstance(stack, ItemStack):
                raise TypeError("drop_resolver must yield ItemStack values")
            if stack.is_empty:
                continue
            copied = stack.copy()
            spawned.append(copied)
        return tuple(spawned)

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
                pos, block_id, block.registry_name, False, bool(can_harvest), self.progress
            )

        drops = self._resolve_drops(block, pos, bool(can_harvest))
        self.world.set_block_state_id(pos, 0)
        for stack in drops:
            self.drop_manager.spawn(pos.x + 0.5, pos.y + 0.5, pos.z + 0.5, stack)
        result = BlockBreakResult(
            pos, block_id, block.registry_name, True, bool(can_harvest), 1.0, drops
        )
        self.reset()
        return result


__all__ = ["BlockBreaking", "BlockBreakResult"]
