"""Tests for source-backed non-combat vanilla food crafting recipes."""
import unittest

from engine.gameplay.crafting import CraftingGrid, RecipeManager
from engine.gameplay.items import ItemRegistry, ItemStack
from engine.gameplay.vanilla_food_recipes import (
    register_vanilla_food_recipe_items, register_vanilla_food_recipes,
)


class TestVanillaFoodRecipes(unittest.TestCase):
    def setUp(self):
        self.items = ItemRegistry()
        self.recipes = register_vanilla_food_recipes(self.items)

    def test_bread_recipe(self):
        grid = CraftingGrid(3, 3)
        wheat = self.items.require_by_name("minecraft:wheat")
        for slot in range(3):
            grid.set_slot(slot, ItemStack(wheat, 1))
        result = grid.craft(self.recipes)
        self.assertEqual(result.item.name, "minecraft:bread")
        self.assertEqual(result.count, 1)

    def test_cookie_recipe_requires_cocoa_dye_metadata(self):
        grid = CraftingGrid(3, 3)
        wheat = self.items.require_by_name("minecraft:wheat")
        dye = self.items.require_by_name("minecraft:dye")
        grid.set_slot(0, ItemStack(wheat, 1))
        grid.set_slot(1, ItemStack(dye, 1, metadata=3))
        grid.set_slot(2, ItemStack(wheat, 1))
        result = grid.craft(self.recipes)
        self.assertEqual(result.item.name, "minecraft:cookie")
        self.assertEqual(result.count, 8)

    def test_wrong_dye_metadata_does_not_make_cookie(self):
        grid = CraftingGrid(3, 3)
        wheat = self.items.require_by_name("minecraft:wheat")
        dye = self.items.require_by_name("minecraft:dye")
        grid.set_slot(0, ItemStack(wheat, 1))
        grid.set_slot(1, ItemStack(dye, 1, metadata=4))
        grid.set_slot(2, ItemStack(wheat, 1))
        self.assertTrue(grid.craft(self.recipes).is_empty)

    def test_cake_recipe_returns_three_buckets(self):
        grid = CraftingGrid(3, 3)
        milk = self.items.require_by_name("minecraft:milk_bucket")
        sugar = self.items.require_by_name("minecraft:sugar")
        egg = self.items.require_by_name("minecraft:egg")
        wheat = self.items.require_by_name("minecraft:wheat")
        for slot in range(3):
            grid.set_slot(slot, ItemStack(milk, 1))
        grid.set_slot(3, ItemStack(sugar, 1))
        grid.set_slot(4, ItemStack(egg, 1))
        grid.set_slot(5, ItemStack(sugar, 1))
        for slot in range(6, 9):
            grid.set_slot(slot, ItemStack(wheat, 1))
        result = grid.craft(self.recipes)
        self.assertEqual(result.item.name, "minecraft:cake")
        self.assertEqual(sum(grid.get_slot(i).count for i in range(3)), 3)
        self.assertTrue(all(grid.get_slot(i).item.name == "minecraft:bucket" for i in range(3)))

    def test_pumpkin_pie_recipe(self):
        grid = CraftingGrid(2, 2)
        grid.set_slot(0, ItemStack(self.items.require_by_name("minecraft:pumpkin"), 1))
        grid.set_slot(1, ItemStack(self.items.require_by_name("minecraft:sugar"), 1))
        grid.set_slot(2, ItemStack(self.items.require_by_name("minecraft:egg"), 1))
        result = grid.craft(self.recipes)
        self.assertEqual(result.item.name, "minecraft:pumpkin_pie")

    def test_mushroom_stew_recipe_returns_bowl(self):
        grid = CraftingGrid(2, 2)
        grid.set_slot(0, ItemStack(self.items.require_by_name("minecraft:brown_mushroom"), 1))
        grid.set_slot(1, ItemStack(self.items.require_by_name("minecraft:red_mushroom"), 1))
        grid.set_slot(2, ItemStack(self.items.require_by_name("minecraft:bowl"), 1))
        result = grid.craft(self.recipes)
        self.assertEqual(result.item.name, "minecraft:mushroom_stew")

    def test_beetroot_soup_recipe(self):
        grid = CraftingGrid(3, 3)
        beetroot = self.items.require_by_name("minecraft:beetroot")
        for slot in range(6):
            grid.set_slot(slot, ItemStack(beetroot, 1))
        grid.set_slot(7, ItemStack(self.items.require_by_name("minecraft:bowl"), 1))
        result = grid.craft(self.recipes)
        self.assertEqual(result.item.name, "minecraft:beetroot_soup")

    def test_recipe_catalogue_can_use_injected_manager(self):
        manager = RecipeManager()
        self.assertIs(register_vanilla_food_recipes(self.items, manager), manager)

    def test_item_catalogue_registration_is_idempotent(self):
        count = len(self.items)
        register_vanilla_food_recipe_items(self.items)
        self.assertEqual(len(self.items), count)


if __name__ == "__main__":
    unittest.main()
