"""Tests for dropped item entities and pickup."""
import unittest

from engine.gameplay import Inventory, Item, ItemStack
from engine.gameplay.drops import EntityItem, ItemDropManager
from engine.world import World


class TestItemDrops(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.inventory = Inventory()
        self.stone = Item(1, "minecraft:stone")

    def test_spawn_registers_entity_and_copies_stack(self):
        source = ItemStack(self.stone, 5)
        drop = ItemDropManager(self.world).spawn(1, 65, 1, source)
        source.shrink(2)
        self.assertIn(drop, self.world.entities)
        self.assertEqual(drop.stack.count, 5)
        self.assertEqual(drop.pickup_delay, 10)

    def test_pickup_blocked_by_delay(self):
        drop = EntityItem(self.world, 0, 64, 0, ItemStack(self.stone, 3), pickup_delay=2)
        self.assertFalse(drop.try_pickup(self.inventory))
        drop.on_update()
        self.assertFalse(drop.try_pickup(self.inventory))
        drop.on_update()
        self.assertTrue(drop.try_pickup(self.inventory))
        self.assertEqual(self.inventory.count_item(self.stone), 3)
        self.assertTrue(drop.dead)

    def test_pickup_transfers_stack_and_removes_entity(self):
        drop = ItemDropManager(self.world).spawn(0, 64, 0, ItemStack(self.stone, 12), pickup_delay=0)
        self.assertTrue(drop.try_pickup(self.inventory))
        self.assertEqual(self.inventory.count_item(self.stone), 12)
        self.assertNotIn(drop, self.world.entities)

    def test_partial_pickup_keeps_remainder(self):
        for i in range(36):
            self.inventory.set_slot(i, ItemStack(self.stone, 64))
        self.inventory.remove_from_slot(0, 5)
        drop = EntityItem(self.world, 0, 64, 0, ItemStack(self.stone, 8), pickup_delay=0)
        self.assertFalse(drop.try_pickup(self.inventory))
        self.assertEqual(drop.stack.count, 3)
        self.assertFalse(drop.dead)

    def test_lifetime_despawns_entity(self):
        drop = EntityItem(self.world, 0, 64, 0, ItemStack(self.stone, 1),
                          pickup_delay=0, lifetime=1)
        self.world.add_entity(drop)
        drop.on_update()
        self.assertTrue(drop.dead)
        self.assertNotIn(drop, self.world.entities)

    def test_empty_stack_cannot_be_dropped(self):
        with self.assertRaises(ValueError):
            EntityItem(self.world, 0, 64, 0, ItemStack.empty())


if __name__ == "__main__":
    unittest.main()
