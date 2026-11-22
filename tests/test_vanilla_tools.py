"""Tests for source-backed vanilla 1.12.2 tool mappings."""
import unittest

from engine.gameplay.items import Item
from engine.gameplay.vanilla_tools import VANILLA_TOOL_MATERIALS, create_vanilla_tool_registry


class TestVanillaToolMappings(unittest.TestCase):
    def setUp(self):
        self.items = {
            "wooden_pickaxe": Item(270, "minecraft:wooden_pickaxe", 1, 59),
            "iron_pickaxe": Item(257, "minecraft:iron_pickaxe", 1, 250),
            "diamond_pickaxe": Item(278, "minecraft:diamond_pickaxe", 1, 1561),
            "golden_axe": Item(286, "minecraft:golden_axe", 1, 32),
            "iron_shovel": Item(256, "minecraft:iron_shovel", 1, 250),
        }
        self.registry = create_vanilla_tool_registry(self.items)

    def test_material_source_values(self):
        self.assertEqual(VANILLA_TOOL_MATERIALS["wooden"].durability, 59)
        self.assertEqual(VANILLA_TOOL_MATERIALS["stone"].enchantability, 5)
        self.assertEqual(VANILLA_TOOL_MATERIALS["iron"].harvest_level, 2)
        self.assertEqual(VANILLA_TOOL_MATERIALS["diamond"].efficiency, 8.0)
        self.assertEqual(VANILLA_TOOL_MATERIALS["golden"].durability, 32)

    def test_tool_speed_uses_vanilla_material_groups(self):
        self.assertEqual(self.registry.dig_speed(self.items["iron_pickaxe"], "stone"), 6.0)
        self.assertEqual(self.registry.dig_speed(self.items["golden_axe"], "planks"), 12.0)
        self.assertEqual(self.registry.dig_speed(self.items["iron_shovel"], "sand"), 6.0)
        self.assertEqual(self.registry.dig_speed(self.items["iron_shovel"], "grass"), 6.0)
        self.assertEqual(self.registry.dig_speed(self.items["iron_shovel"], "stone"), 1.0)

    def test_pickaxe_harvest_tiers(self):
        self.assertFalse(self.registry.can_harvest(self.items["iron_pickaxe"], "obsidian"))
        self.assertTrue(self.registry.can_harvest(self.items["diamond_pickaxe"], "obsidian"))
        self.assertTrue(self.registry.can_harvest(self.items["iron_pickaxe"], "iron_ore"))
        self.assertFalse(self.registry.can_harvest(self.items["wooden_pickaxe"], "iron_ore"))

    def test_shovel_snow_harvest_rule(self):
        self.assertTrue(self.registry.can_harvest(self.items["iron_shovel"], "snow_layer"))
        self.assertFalse(self.registry.can_harvest(self.items["iron_pickaxe"], "snow_layer"))

    def test_unknown_names_and_wrong_durability_are_rejected(self):
        with self.assertRaises(ValueError):
            create_vanilla_tool_registry({"wooden_sword": self.items["wooden_pickaxe"]})
        wrong = Item(999, "test:wrong_pickaxe", 1, 58)
        with self.assertRaises(ValueError):
            create_vanilla_tool_registry({"wooden_pickaxe": wrong})


if __name__ == "__main__":
    unittest.main()