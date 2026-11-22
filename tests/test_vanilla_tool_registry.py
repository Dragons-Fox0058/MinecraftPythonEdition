"""Tests for source-backed vanilla 1.12.2 tool definitions."""
import unittest

from engine.gameplay.items import Item
from engine.gameplay.vanilla_tools import (
    VANILLA_TOOL_MATERIALS,
    create_vanilla_tool_registry,
)


class TestVanillaToolRegistry(unittest.TestCase):
    def setUp(self):
        self.items = {}
        item_id = 2000
        for material_name, material in VANILLA_TOOL_MATERIALS.items():
            for tool_class in ("pickaxe", "axe", "shovel"):
                name = f"{material_name}_{tool_class}"
                self.items[name] = Item(
                    item_id, f"minecraft:{name}",
                    max_stack_size=1, max_damage=material.durability,
                )
                item_id += 1
        self.registry = create_vanilla_tool_registry(self.items)

    def test_all_five_material_tiers_match_1122_values(self):
        expected = {
            "wooden": (59, 2.0, 0, 15, 0.0),
            "stone": (131, 4.0, 1, 5, 1.0),
            "iron": (250, 6.0, 2, 14, 2.0),
            "diamond": (1561, 8.0, 3, 10, 3.0),
            "golden": (32, 12.0, 0, 22, 0.0),
        }
        actual = {
            name: (
                material.durability, material.efficiency,
                material.harvest_level, material.enchantability,
                material.damage_vs_entity,
            )
            for name, material in VANILLA_TOOL_MATERIALS.items()
        }
        self.assertEqual(actual, expected)

    def test_tool_classes_receive_expected_effective_blocks(self):
        self.assertEqual(
            self.registry.dig_speed(self.items["wooden_pickaxe"], "stone"), 2.0
        )
        self.assertEqual(
            self.registry.dig_speed(self.items["iron_axe"], "log"), 6.0
        )
        self.assertEqual(
            self.registry.dig_speed(self.items["stone_shovel"], "dirt"), 4.0
        )
        self.assertEqual(
            self.registry.dig_speed(self.items["iron_pickaxe"], "dirt"), 1.0
        )

    def test_empty_hand_harvest_rules_match_vanilla(self):
        empty_hand = create_vanilla_tool_registry({})
        # Java 1.12.2 requires a pickaxe for stone and ores, but not dirt.
        self.assertFalse(empty_hand.can_harvest(None, "stone"))
        self.assertFalse(empty_hand.can_harvest(None, "iron_ore"))
        self.assertTrue(empty_hand.can_harvest(None, "dirt"))
        self.assertTrue(empty_hand.can_harvest(None, "sand"))

    def test_vanilla_harvest_levels(self):
        self.assertFalse(
            self.registry.can_harvest(self.items["wooden_pickaxe"], "iron_ore")
        )
        self.assertTrue(
            self.registry.can_harvest(self.items["stone_pickaxe"], "iron_ore")
        )
        self.assertFalse(
            self.registry.can_harvest(self.items["iron_pickaxe"], "obsidian")
        )
        self.assertTrue(
            self.registry.can_harvest(self.items["diamond_pickaxe"], "obsidian")
        )
        self.assertFalse(
            self.registry.can_harvest(self.items["golden_pickaxe"], "diamond_ore")
        )
        self.assertTrue(
            self.registry.can_harvest(self.items["stone_shovel"], "snow_layer")
        )


if __name__ == "__main__":
    unittest.main()
