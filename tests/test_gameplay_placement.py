"""Tests for block placement."""
import unittest

from engine.core import BlockPos, EnumFacing
from engine.gameplay.items import Item, ItemStack
from engine.gameplay.placement import BlockPlacement
from engine.world import World
import engine.blocks.vanilla_blocks as VB


class TestBlockPlacement(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.pos = BlockPos(0, 64, 0)
        self.block_item = Item(500, "test:stone_block")
        self.stack = ItemStack(self.block_item, 4)
        self.placement = BlockPlacement(
            self.world, lambda item: VB.STONE if item is self.block_item else None
        )

    def test_place_into_air(self):
        result = self.placement.place(self.stack, self.pos, EnumFacing.UP)
        self.assertTrue(result.placed)
        self.assertEqual(self.world.get_block_state_id(self.pos), VB.STONE.block_id)
        self.assertEqual(self.stack.count, 3)

    def test_place_adjacent_to_solid_block(self):
        self.world.set_block_state_id(self.pos, VB.DIRT.block_id)
        result = self.placement.place(self.stack, self.pos, EnumFacing.EAST)
        self.assertTrue(result.placed)
        self.assertEqual(result.pos, self.pos.east())
        self.assertEqual(self.world.get_block_state_id(self.pos.east()), VB.STONE.block_id)

    def test_replaceable_plant_is_replaced_in_place(self):
        self.world.set_block_state_id(self.pos, VB.TALLGRASS.block_id)
        result = self.placement.place(self.stack, self.pos, EnumFacing.UP)
        self.assertTrue(result.placed)
        self.assertEqual(result.pos, self.pos)

    def test_occupied_target_does_not_consume_item(self):
        self.world.set_block_state_id(self.pos, VB.DIRT.block_id)
        self.world.set_block_state_id(self.pos.up(), VB.STONE.block_id)
        result = self.placement.place(self.stack, self.pos, EnumFacing.UP)
        self.assertFalse(result.placed)
        self.assertEqual(result.reason, "occupied")
        self.assertEqual(self.stack.count, 4)

    def test_non_block_item_rejected(self):
        result = self.placement.place(ItemStack(Item(501, "test:stick"), 1),
                                      self.pos, EnumFacing.UP)
        self.assertFalse(result.placed)
        self.assertEqual(result.reason, "not_a_block_item")

    def test_unregistered_block_rejected(self):
        unregistered = __import__("engine.blocks", fromlist=["Block"]).Block(
            "test:unregistered", 9999, VB.STONE.material
        )
        placement = BlockPlacement(self.world, lambda item: unregistered)
        result = placement.place(self.stack, self.pos, EnumFacing.UP)
        self.assertFalse(result.placed)
        self.assertEqual(result.reason, "unregistered_block")
        self.assertEqual(self.stack.count, 4)

    def test_empty_stack_rejected(self):
        result = self.placement.place(ItemStack.empty(), self.pos, EnumFacing.UP)
        self.assertFalse(result.placed)
        self.assertEqual(result.reason, "empty_stack")

    def test_collision_callback_prevents_placement(self):
        result = self.placement.place(self.stack, self.pos, EnumFacing.UP,
                                      can_place=lambda block, pos: False)
        self.assertFalse(result.placed)
        self.assertEqual(result.reason, "collision")
        self.assertEqual(self.stack.count, 4)

    def test_world_height_is_checked(self):
        high = BlockPos(0, 255, 0)
        self.world.set_block_state_id(high, VB.STONE.block_id)
        result = self.placement.place(self.stack, high, EnumFacing.UP)
        self.assertFalse(result.placed)
        self.assertEqual(result.reason, "out_of_world")
        self.assertEqual(self.stack.count, 4)

    def test_item_is_consumed_only_after_success(self):
        self.assertTrue(self.placement.place(self.stack, self.pos, EnumFacing.UP).placed)
        self.assertEqual(self.stack.count, 3)


if __name__ == "__main__":
    unittest.main()
