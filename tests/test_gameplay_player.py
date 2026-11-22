"""Tests for the integrated player gameplay controller."""
import unittest

from engine.core import BlockPos, EnumFacing
from engine.entities import EntityPlayer
from engine.gameplay import FoodProperties, FoodRegistry, Item, ItemStack
from engine.gameplay.player import PlayerController
from engine.world import World
import engine.blocks.vanilla_blocks as VB


class TestPlayerController(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.player = EntityPlayer(self.world, 0, 64, 0)
        self.controller = PlayerController(self.player)
        self.stone_item = Item(500, "test:stone_block")
        self.apple = Item(501, "test:apple")
        self.controller.food_registry.register(self.apple, FoodProperties(4, 0.3))

    def test_controller_attaches_player_components(self):
        self.assertIs(self.player.inventory, self.controller.inventory)
        self.assertIs(self.player.hunger, self.controller.hunger)
        self.assertIn(self.player, self.world.entities)

    def test_hotbar_and_held_item(self):
        self.controller.inventory.set_slot(1, ItemStack(self.stone_item, 5))
        self.controller.select_hotbar_slot(1)
        self.assertEqual(self.controller.held_item.count, 5)

    def test_world_tick_updates_player_hunger(self):
        self.controller.hunger.food_level = 0
        self.controller.hunger.saturation = 0
        self.player.health = 2
        for _ in range(80):
            self.world.tick()
        self.assertEqual(self.world.world_time.total_time, 80)
        self.assertLess(self.player.health, 2)

    def test_block_breaking_is_exposed(self):
        pos = BlockPos(0, 64, 1)
        self.world.set_block_state_id(pos, VB.TALLGRASS.block_id)
        result = self.controller.break_block(pos)
        self.assertTrue(result.broken)

    def test_block_placement_uses_held_item(self):
        self.controller.inventory.set_slot(0, ItemStack(self.stone_item, 2))
        result = self.controller.place_block(
            BlockPos(2, 64, 2), EnumFacing.UP,
            lambda item: VB.STONE if item is self.stone_item else None,
        )
        self.assertTrue(result.placed)
        self.assertEqual(self.controller.held_item.count, 1)

    def test_explicit_empty_food_registry_is_preserved(self):
        registry = FoodRegistry()
        player = EntityPlayer(self.world, 4, 64, 4)
        controller = PlayerController(player, food_registry=registry)
        self.assertIs(controller.food_registry, registry)

    def test_consume_food_from_selected_hotbar_slot(self):
        self.controller.hunger.food_level = 10
        self.controller.inventory.set_slot(0, ItemStack(self.apple, 2))
        self.assertTrue(self.controller.consume_food())
        self.assertEqual(self.controller.hunger.food_level, 14)
        self.assertEqual(self.controller.held_item.count, 1)

    def test_drop_and_pickup(self):
        source = ItemStack(self.stone_item, 3)
        drop = self.controller.drop_item(source)
        self.assertTrue(source.is_empty)
        self.assertIsNotNone(drop)
        self.assertTrue(drop.stack.count == 3)
        drop.pickup_delay = 0
        self.assertTrue(self.controller.try_pickup(drop))
        self.assertEqual(self.controller.inventory.count_item(self.stone_item), 3)


if __name__ == "__main__":
    unittest.main()
