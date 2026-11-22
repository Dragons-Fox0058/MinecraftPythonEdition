"""Tests for the complete 1.12.2 sword and hoe material tiers."""
import unittest

from engine.gameplay.crafting import CraftingGrid
from engine.gameplay.items import Item, ItemStack
from engine.gameplay.vanilla_equipment import (
    create_vanilla_equipment_items, create_vanilla_equipment_recipes,
)


class TestVanillaEquipment(unittest.TestCase):
    def setUp(self):
        self.items, self.stats = create_vanilla_equipment_items()
        self.ingredients = {
            "planks": Item(5, "test:planks", has_subtypes=True),
            "cobblestone": Item(4, "test:cobblestone"),
            "iron_ingot": Item(265, "test:iron_ingot"),
            "diamond": Item(264, "test:diamond"),
            "gold_ingot": Item(266, "test:gold_ingot"),
            "stick": Item(280, "test:stick"),
        }
        self.recipes = create_vanilla_equipment_recipes(self.items, self.ingredients)

    def test_all_ten_equipment_items_use_legacy_ids_and_durability(self):
        self.assertEqual(len(self.items), 10)
        expected_ids = {
            "wooden_sword": 268, "stone_sword": 272, "iron_sword": 267,
            "diamond_sword": 276, "golden_sword": 283,
            "wooden_hoe": 290, "stone_hoe": 291, "iron_hoe": 292,
            "diamond_hoe": 293, "golden_hoe": 294,
        }
        for name, item_id in expected_ids.items():
            self.assertEqual(self.items[name].item_id, item_id)
            self.assertEqual(self.items[name].max_stack_size, 1)
            self.assertEqual(self.items[name].max_damage, self.stats[name].durability)

    def test_sword_damage_increases_by_material_tier(self):
        self.assertEqual(self.stats["wooden_sword"].attack_damage, 4.0)
        self.assertEqual(self.stats["stone_sword"].attack_damage, 5.0)
        self.assertEqual(self.stats["iron_sword"].attack_damage, 6.0)
        self.assertEqual(self.stats["diamond_sword"].attack_damage, 7.0)
        self.assertEqual(self.stats["golden_sword"].attack_damage, 4.0)

    def test_all_ten_recipes_are_registered(self):
        self.assertEqual(len(self.recipes), 10)

    def test_sword_recipe_consumes_two_materials_and_a_stick(self):
        grid = CraftingGrid(3, 3)
        grid.set_slot(0, ItemStack(self.ingredients["diamond"], 1))
        grid.set_slot(3, ItemStack(self.ingredients["diamond"], 1))
        grid.set_slot(6, ItemStack(self.ingredients["stick"], 1))
        result = grid.craft(self.recipes)
        self.assertIs(result.item, self.items["diamond_sword"])
        self.assertTrue(all(stack.is_empty for stack in grid.slots))

    def test_hoe_recipe_supports_mirrored_pattern(self):
        grid = CraftingGrid(3, 3)
        grid.set_slot(1, ItemStack(self.ingredients["iron_ingot"], 1))
        grid.set_slot(2, ItemStack(self.ingredients["iron_ingot"], 1))
        grid.set_slot(4, ItemStack(self.ingredients["stick"], 1))
        grid.set_slot(7, ItemStack(self.ingredients["stick"], 1))
        result = grid.craft(self.recipes)
        self.assertIs(result.item, self.items["iron_hoe"])

    def test_metadata_sensitive_planks_can_make_wooden_sword(self):
        grid = CraftingGrid(3, 3)
        grid.set_slot(1, ItemStack(self.ingredients["planks"], 1, metadata=2))
        grid.set_slot(4, ItemStack(self.ingredients["planks"], 1, metadata=2))
        grid.set_slot(7, ItemStack(self.ingredients["stick"], 1))
        result = grid.craft(self.recipes)
        self.assertIs(result.item, self.items["wooden_sword"])


if __name__ == "__main__":
    unittest.main()
