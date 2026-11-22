"""Tests for block breaking progress and optional loot drops."""
import unittest

from engine.core import BlockPos
from engine.gameplay.breaking import BlockBreaking
from engine.gameplay.items import Item, ItemStack
from engine.gameplay.tools import ToolDefinition, ToolMaterial, ToolRegistry
from engine.world import World
import engine.blocks.vanilla_blocks as VB


class TestBlockBreaking(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.breaking = BlockBreaking(self.world)
        self.pos = BlockPos(0, 64, 0)

    def test_relative_hardness_matches_vanilla_divisors(self):
        self.assertAlmostEqual(BlockBreaking.relative_hardness(1.5, 1.0, True), 1 / 45)
        self.assertAlmostEqual(BlockBreaking.relative_hardness(1.5, 1.0, False), 1 / 150)

    def test_unbreakable_block_never_progresses(self):
        self.assertEqual(BlockBreaking.relative_hardness(-1, 10, True), 0)

    def test_zero_hardness_is_instant(self):
        self.assertEqual(BlockBreaking.relative_hardness(0, 1, False), 1)

    def test_negative_speed_rejected(self):
        with self.assertRaises(ValueError):
            BlockBreaking.relative_hardness(1, -1, True)

    def test_damage_accumulates_until_block_breaks(self):
        self.world.set_block_state_id(self.pos, VB.DIRT.block_id)
        result = self.breaking.damage_block(self.pos, dig_speed=1, can_harvest=True)
        self.assertFalse(result.broken)
        self.assertGreater(result.progress, 0)
        for _ in range(100):
            result = self.breaking.damage_block(self.pos, dig_speed=100, can_harvest=True)
            if result.broken:
                break
        self.assertTrue(result.broken)
        self.assertEqual(result.block_id, VB.DIRT.block_id)
        self.assertTrue(self.world.is_air(self.pos))
        self.assertIsNone(self.breaking.target)

    def test_hardness_zero_block_breaks_immediately(self):
        self.world.set_block_state_id(self.pos, VB.TALLGRASS.block_id)
        result = self.breaking.damage_block(self.pos)
        self.assertTrue(result.broken)
        self.assertTrue(self.world.is_air(self.pos))

    def test_unbreakable_bedrock_does_not_break(self):
        self.world.set_block_state_id(self.pos, VB.BEDROCK.block_id)
        result = self.breaking.damage_block(self.pos, dig_speed=10000, can_harvest=True)
        self.assertFalse(result.broken)
        self.assertEqual(self.world.get_block_state_id(self.pos), VB.BEDROCK.block_id)

    def test_changing_target_resets_progress(self):
        other = BlockPos(1, 64, 0)
        self.world.set_block_state_id(self.pos, VB.STONE.block_id)
        self.world.set_block_state_id(other, VB.STONE.block_id)
        first = self.breaking.damage_block(self.pos, dig_speed=1, can_harvest=True)
        second = self.breaking.damage_block(other, dig_speed=1, can_harvest=True)
        self.assertGreater(first.progress, 0)
        self.assertEqual(second.progress, first.progress)

    def test_air_target_resets_progress(self):
        self.world.set_block_state_id(self.pos, VB.DIRT.block_id)
        self.breaking.damage_block(self.pos, dig_speed=1, can_harvest=True)
        result = self.breaking.damage_block(BlockPos(3, 64, 0))
        self.assertFalse(result.broken)
        self.assertIsNone(self.breaking.target)
        self.assertEqual(self.breaking.progress, 0)

    def test_harvested_block_spawns_resolved_drops(self):
        item = Item(900, "test:dirt_drop")
        breaking = BlockBreaking(
            self.world, drop_resolver=lambda block, pos: [ItemStack(item, 2)]
        )
        self.world.set_block_state_id(self.pos, VB.DIRT.block_id)
        result = breaking.damage_block(self.pos, dig_speed=1000, can_harvest=True)
        self.assertTrue(result.broken)
        self.assertEqual(len(result.drops), 1)
        self.assertEqual(result.drops[0].count, 2)
        self.assertEqual(len(self.world.entities), 1)

    def test_no_drops_when_tool_cannot_harvest(self):
        item = Item(901, "test:no_drop")
        breaking = BlockBreaking(
            self.world, drop_resolver=lambda block, pos: [ItemStack(item, 1)]
        )
        self.world.set_block_state_id(self.pos, VB.DIRT.block_id)
        result = breaking.damage_block(self.pos, dig_speed=1000, can_harvest=False)
        self.assertTrue(result.broken)
        self.assertEqual(result.drops, ())
        self.assertEqual(len(self.world.entities), 0)

    def test_drop_resolver_failure_does_not_remove_block(self):
        def broken_resolver(block, pos):
            raise RuntimeError("loot table unavailable")
        breaking = BlockBreaking(self.world, drop_resolver=broken_resolver)
        self.world.set_block_state_id(self.pos, VB.DIRT.block_id)
        with self.assertRaises(RuntimeError):
            breaking.damage_block(self.pos, dig_speed=1000, can_harvest=True)
        self.assertEqual(self.world.get_block_state_id(self.pos), VB.DIRT.block_id)

    def test_tool_registry_controls_harvest_and_durability(self):
        material = ToolMaterial("stone", 131, 4.0, 1)
        pickaxe = Item(910, "test:stone_pickaxe", max_stack_size=1, max_damage=131)
        tools = ToolRegistry()
        tools.register(ToolDefinition(
            pickaxe, "pickaxe", material, frozenset({"stone"})
        ))
        tools.set_harvest_requirement("stone", "pickaxe", 1)
        item = Item(911, "test:stone_drop")
        breaking = BlockBreaking(
            self.world,
            drop_resolver=lambda block, pos: [ItemStack(item, 1)],
            tool_registry=tools,
        )
        held = ItemStack(pickaxe, 1)
        self.world.set_block_state_id(self.pos, VB.STONE.block_id)
        result = breaking.damage_block(self.pos, dig_speed=1000, tool_stack=held)
        self.assertTrue(result.broken)
        self.assertTrue(result.can_harvest)
        self.assertEqual(held.damage, 1)
        self.assertEqual(len(result.drops), 1)

    def test_wrong_tool_cannot_harvest_required_block(self):
        wood = ToolMaterial("wood", 59, 2.0, 0)
        pickaxe = Item(912, "test:wood_pickaxe", max_stack_size=1, max_damage=59)
        tools = ToolRegistry()
        tools.register(ToolDefinition(
            pickaxe, "pickaxe", wood, frozenset({"stone"})
        ))
        tools.set_harvest_requirement("stone", "pickaxe", 1)
        item = Item(913, "test:stone_drop")
        breaking = BlockBreaking(
            self.world,
            drop_resolver=lambda block, pos: [ItemStack(item, 1)],
            tool_registry=tools,
        )
        held = ItemStack(pickaxe, 1)
        self.world.set_block_state_id(self.pos, VB.STONE.block_id)
        result = breaking.damage_block(self.pos, dig_speed=1000, tool_stack=held)
        self.assertTrue(result.broken)
        self.assertFalse(result.can_harvest)
        self.assertEqual(result.drops, ())
        self.assertEqual(held.damage, 1)

    def test_do_tile_drops_rule_disables_drops(self):
        item = Item(902, "test:disabled_drop")
        breaking = BlockBreaking(
            self.world, drop_resolver=lambda block, pos: [ItemStack(item, 1)]
        )
        self.world.game_rules.set("doTileDrops", False)
        self.world.set_block_state_id(self.pos, VB.DIRT.block_id)
        result = breaking.damage_block(self.pos, dig_speed=1000, can_harvest=True)
        self.assertTrue(result.broken)
        self.assertEqual(result.drops, ())
        self.assertEqual(len(self.world.entities), 0)


if __name__ == "__main__":
    unittest.main()
