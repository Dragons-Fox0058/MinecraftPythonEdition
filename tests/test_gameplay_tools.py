"""Tests for explicit tool speed and harvest-level rules."""
import unittest

from engine.gameplay.items import Item
from engine.gameplay.tools import ToolDefinition, ToolMaterial, ToolRegistry


class TestToolRegistry(unittest.TestCase):
    def setUp(self):
        self.wood = ToolMaterial("wood", 59, 2.0, 0)
        self.stone = ToolMaterial("stone", 131, 4.0, 1)
        self.iron = ToolMaterial("iron", 250, 6.0, 2)
        self.registry = ToolRegistry()
        self.pickaxe = Item(270, "test:wood_pickaxe", max_stack_size=1, max_damage=59)
        self.stone_pickaxe = Item(274, "test:stone_pickaxe", max_stack_size=1, max_damage=131)
        self.registry.register(ToolDefinition(self.pickaxe, "pickaxe", self.wood, frozenset({"stone", "cobblestone"})))
        self.registry.register(ToolDefinition(self.stone_pickaxe, "pickaxe", self.stone, frozenset({"stone", "cobblestone", "iron_ore"})))

    def test_effective_tool_speed(self):
        self.assertEqual(self.registry.dig_speed(self.pickaxe, "stone"), 2.0)
        self.assertEqual(self.registry.dig_speed(self.pickaxe, "dirt"), 1.0)
        self.assertEqual(self.registry.dig_speed(None, "stone"), 1.0)

    def test_harvest_level_requirement(self):
        self.registry.set_harvest_requirement("iron_ore", "pickaxe", 2)
        self.assertFalse(self.registry.can_harvest(self.pickaxe, "iron_ore"))
        self.assertTrue(self.registry.can_harvest(self.stone_pickaxe, "iron_ore") is False)
        iron_pickaxe = Item(257, "test:iron_pickaxe", max_stack_size=1, max_damage=250)
        self.registry.register(ToolDefinition(iron_pickaxe, "pickaxe", self.iron, frozenset({"iron_ore"})))
        self.assertTrue(self.registry.can_harvest(iron_pickaxe, "iron_ore"))

    def test_blocks_without_requirement_are_harvestable(self):
        self.assertTrue(self.registry.can_harvest(None, "dirt"))

    def test_duplicate_tool_and_requirement_rejected(self):
        with self.assertRaises(ValueError):
            self.registry.register(ToolDefinition(self.pickaxe, "pickaxe", self.wood, frozenset()))
        self.registry.set_harvest_requirement("diamond_ore", "pickaxe", 2)
        with self.assertRaises(ValueError):
            self.registry.set_harvest_requirement("diamond_ore", "pickaxe", 2)

    def test_material_rejects_non_finite_values(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(efficiency=value):
                with self.assertRaises(ValueError):
                    ToolMaterial("invalid", 10, value, 0)
            with self.subTest(damage=value):
                with self.assertRaises(ValueError):
                    ToolMaterial("invalid", 10, 1.0, 0, damage_vs_entity=value)

    def test_definition_requires_immutable_effective_block_set(self):
        item = Item(901, "test:mutable_tool", max_stack_size=1, max_damage=59)
        with self.assertRaises(TypeError):
            ToolDefinition(item, "pickaxe", self.wood, {"stone"})

    def test_item_durability_must_match_material(self):
        wrong = Item(999, "test:wrong_tool", max_stack_size=1, max_damage=58)
        with self.assertRaises(ValueError):
            ToolDefinition(wrong, "pickaxe", self.wood, frozenset())


if __name__ == "__main__":
    unittest.main()