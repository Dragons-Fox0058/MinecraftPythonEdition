"""Block placement using an injected Item-to-Block resolver."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from engine.blocks import Block
from engine.core import BlockPos, EnumFacing
from engine.gameplay.items import ItemStack


@dataclass(frozen=True)
class PlacementResult:
    placed: bool
    pos: BlockPos
    block_id: int | None
    reason: str


class BlockPlacement:
    """Places blocks without assuming unverified legacy ItemBlock numeric IDs.

    The resolver must return the Block represented by an item, or None when
    the held item is not a placeable block item.
    """

    def __init__(self, world, block_resolver: Callable) -> None:
        if not callable(block_resolver):
            raise TypeError("block_resolver must be callable")
        self.world = world
        self.block_resolver = block_resolver

    def place(self, stack: ItemStack, clicked_pos: BlockPos, face: EnumFacing,
              can_place: Callable[[Block, BlockPos], bool] | None = None) -> PlacementResult:
        if not isinstance(stack, ItemStack):
            raise TypeError("stack must be an ItemStack")
        if not isinstance(clicked_pos, BlockPos):
            raise TypeError("clicked_pos must be a BlockPos")
        if not isinstance(face, EnumFacing):
            raise TypeError("face must be an EnumFacing")
        if stack.is_empty:
            return PlacementResult(False, clicked_pos, None, "empty_stack")

        block = self.block_resolver(stack.item)
        if block is None:
            return PlacementResult(False, clicked_pos, None, "not_a_block_item")
        if not isinstance(block, Block):
            raise TypeError("block_resolver must return a Block or None")

        clicked_state = self.world.get_block_state(clicked_pos)
        if clicked_state.block.is_replaceable():
            target = clicked_pos
        else:
            target = clicked_pos.offset(face)

        if not self.world.is_in_world_bounds(target.y):
            return PlacementResult(False, target, block.block_id, "out_of_world")
        existing = self.world.get_block_state(target)
        if not existing.block.is_replaceable():
            return PlacementResult(False, target, block.block_id, "occupied")
        if can_place is not None and not can_place(block, target):
            return PlacementResult(False, target, block.block_id, "collision")

        self.world.set_block_state_id(target, block.block_id)
        stack.shrink(1)
        return PlacementResult(True, target, block.block_id, "placed")


__all__ = ["BlockPlacement", "PlacementResult"]
