"""Tests for block loot table generation and block-breaking integration."""
import random
import unittest

from engine.core import BlockPos
from engine.gameplay.items import Item, ItemStack
from engine.gameplay.loot import BlockLootTable, LootEntry, LootTableRegistry
from engine.gameplay.breaking import BlockBreaking
from engine.world import World
import engine.blocks.vanilla_blocks as VB


class TestLootTables(unittest.TestCase):
    def setUp(self):
        self.item = Item(5000, "test:stone_drop", max_stack_size=64)
        self.registry = LootTableRegistry()

    def test_harvest_requirement_filters_loot(self):
        table = BlockLootTable((LootEntry(self.item, 1, 1, requires_harvest=True),))
        self.assertEqual(table.generate(False, random.Random(1)), ())
        self.assertEqual(table.generate(True, random.Random(1))[0].count, 1)

    def test_weighted_selection_and_count_are_deterministic(self):
        other = Item(5001, "test:other_drop", max_stack_size=64)
        table = BlockLootTable((
            LootEntry(self.item, 2, 4, weight=1),
            LootEntry(other, 1, 1, weight=3),
        ))
        first = table.generate(True, random.Random(1234))
        second = table.generate(True, random.Random(1234))
        self.assertEqual([(s.item, s.count) for s in first],
                         [(s.item, s.count) for s in second])

    def test_registry_rejects_duplicates_and_unknown_tables_return_empty(self):
        table = BlockLootTable((LootEntry(self.item),))
        self.registry.register("minecraft:stone", table)
        with self.assertRaises(ValueError):
            self.registry.register("minecraft:stone", table)
        self.assertEqual(self.registry.generate("minecraft:missing", True), ())

    def test_block_breaking_spawns_registered_loot(self):
        world = World()
        pos = BlockPos(0, 64, 0)
        world.set_block_state_id(pos, VB.STONE.block_id)
        registry = LootTableRegistry()
        registry.register(
            "stone", BlockLootTable((LootEntry(self.item, 1, 1),))
        )
        breaking = BlockBreaking(world, loot_registry=registry)
        result = breaking.damage_block(pos, dig_speed=1000.0, can_harvest=True)
        self.assertTrue(result.broken)
        self.assertEqual(len(result.drops), 1)
        self.assertTrue(any(getattr(e, "stack", None) is not None
                            and e.stack.item is self.item for e in world.entities))

    def test_entry_rejects_invalid_counts(self):
        with self.assertRaises(ValueError):
            LootEntry(self.item, min_count=3, max_count=2)


if __name__ == "__main__":
    unittest.main()
