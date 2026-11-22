"""Tests for dropped item entities and pickup."""
import unittest

from engine.core import BlockPos
import engine.blocks.vanilla_blocks as VB
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
        self.assertTrue(drop.try_pickup(self.inventory))
        self.assertEqual(drop.stack.count, 3)
        self.assertFalse(drop.dead)

    def test_merge_compatible_item_entities(self):
        older = EntityItem(self.world, 0, 64, 0, ItemStack(self.stone, 10), pickup_delay=5)
        newer = EntityItem(self.world, 0.2, 64, 0, ItemStack(self.stone, 12), pickup_delay=8)
        self.world.add_entity(older)
        self.world.add_entity(newer)
        self.assertTrue(older.try_merge(newer))
        self.assertEqual(newer.stack.count, 22)
        self.assertEqual(newer.age, 0)
        self.assertEqual(newer.pickup_delay, 8)
        self.assertTrue(older.dead)
        self.assertNotIn(older, self.world.entities)

    def test_merge_partially_fills_stack_and_keeps_remainder(self):
        first = EntityItem(self.world, 0, 64, 0, ItemStack(self.stone, 40))
        second = EntityItem(self.world, 0, 64, 0, ItemStack(self.stone, 30))
        self.assertTrue(first.try_merge(second))
        self.assertEqual(first.stack.count, 64)
        self.assertEqual(second.stack.count, 6)
        self.assertFalse(first.dead)
        self.assertFalse(second.dead)

    def test_merge_rejects_different_metadata_for_subtypes(self):
        dye = Item(2, "test:dye", has_subtypes=True)
        first = EntityItem(self.world, 0, 64, 0, ItemStack(dye, 2, metadata=1))
        second = EntityItem(self.world, 0, 64, 0, ItemStack(dye, 2, metadata=2))
        self.assertFalse(first.try_merge(second))

    def test_merge_rejects_different_nbt(self):
        first = EntityItem(self.world, 0, 64, 0, ItemStack(self.stone, 2, nbt={"x": 1}))
        second = EntityItem(self.world, 0, 64, 0, ItemStack(self.stone, 2, nbt={"x": 2}))
        self.assertFalse(first.try_merge(second))

    def test_infinite_pickup_delay_prevents_merging(self):
        first = EntityItem(self.world, 0, 64, 0, ItemStack(self.stone, 2),
                           pickup_delay=EntityItem.INFINITE_PICKUP_DELAY)
        second = EntityItem(self.world, 0, 64, 0, ItemStack(self.stone, 2))
        self.assertFalse(first.try_merge(second))

    def test_periodic_search_merges_nearby_entities(self):
        self.world.set_block_state_id(BlockPos(0, 63, 0), VB.STONE.block_id)
        first = EntityItem(self.world, 0, 64, 0, ItemStack(self.stone, 2))
        second = EntityItem(self.world, 0.2, 64, 0, ItemStack(self.stone, 3))
        self.world.add_entity(first)
        self.world.add_entity(second)
        for _ in range(25):
            first.on_update()
            second.on_update()
            if first.dead or second.dead:
                break
        self.assertTrue(first.dead or second.dead)
        survivor = second if first.dead else first
        self.assertEqual(survivor.stack.count, 5)

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
