"""Tests for shaped and shapeless crafting."""
import unittest

from engine.gameplay import Item, ItemStack
from engine.gameplay.crafting import (
    CraftingGrid, Ingredient, RecipeManager, ShapedRecipe, ShapelessRecipe,
)


class TestCrafting(unittest.TestCase):
    def setUp(self):
        self.wood = Item(1, "test:wood")
        self.stick = Item(2, "test:stick")
        self.plank = Item(3, "test:plank")
        self.red_dye = Item(4, "test:dye", has_subtypes=True)

    def test_shaped_recipe_matches_offset_pattern(self):
        grid = CraftingGrid(3, 3)
        recipe = ShapedRecipe(1, 2, [Ingredient(self.wood), Ingredient(self.wood)],
                              ItemStack(self.stick, 4))
        manager = RecipeManager()
        manager.register(recipe)
        grid.set_slot(2, ItemStack(self.wood, 3))
        grid.set_slot(5, ItemStack(self.wood, 1))
        self.assertIs(grid.find_recipe(manager), recipe)

    def test_shaped_recipe_mirrors_by_default(self):
        grid = CraftingGrid(2, 2)
        recipe = ShapedRecipe(2, 1, [Ingredient(self.wood), None],
                              ItemStack(self.plank, 1))
        manager = RecipeManager()
        manager.register(recipe)
        grid.set_slot(1, ItemStack(self.wood, 1))
        self.assertIs(grid.find_recipe(manager), recipe)

    def test_shaped_recipe_can_disable_mirroring(self):
        grid = CraftingGrid(2, 1)
        recipe = ShapedRecipe(2, 1, [Ingredient(self.wood), None],
                              ItemStack(self.plank, 1), mirrored=False)
        manager = RecipeManager()
        manager.register(recipe)
        grid.set_slot(1, ItemStack(self.wood, 1))
        self.assertIsNone(grid.find_recipe(manager))

    def test_shaped_recipe_rejects_extra_items(self):
        grid = CraftingGrid(2, 2)
        recipe = ShapedRecipe(1, 1, [Ingredient(self.wood)], ItemStack(self.plank, 1))
        manager = RecipeManager()
        manager.register(recipe)
        grid.set_slot(0, ItemStack(self.wood, 1))
        grid.set_slot(1, ItemStack(self.wood, 1))
        self.assertIsNone(grid.find_recipe(manager))

    def test_shapeless_recipe_ignores_slot_order(self):
        grid = CraftingGrid(2, 2)
        recipe = ShapelessRecipe(
            [Ingredient(self.wood), Ingredient(self.stick)], ItemStack(self.plank, 2)
        )
        manager = RecipeManager()
        manager.register(recipe)
        grid.set_slot(0, ItemStack(self.stick, 5))
        grid.set_slot(3, ItemStack(self.wood, 2))
        self.assertIs(grid.find_recipe(manager), recipe)

    def test_shapeless_wildcard_metadata_matching(self):
        grid = CraftingGrid(2, 2)
        recipe = ShapelessRecipe(
            [Ingredient(self.red_dye), Ingredient(self.red_dye, metadata=1)],
            ItemStack(self.plank, 1),
        )
        manager = RecipeManager()
        manager.register(recipe)
        grid.set_slot(0, ItemStack(self.red_dye, 1, metadata=1))
        grid.set_slot(1, ItemStack(self.red_dye, 1, metadata=2))
        self.assertIs(grid.find_recipe(manager), recipe)

    def test_craft_consumes_one_from_each_occupied_slot(self):
        grid = CraftingGrid(2, 2)
        manager = RecipeManager()
        manager.register(ShapelessRecipe(
            [Ingredient(self.wood), Ingredient(self.stick)], ItemStack(self.plank, 4)
        ))
        grid.set_slot(0, ItemStack(self.wood, 3))
        grid.set_slot(1, ItemStack(self.stick, 2))
        output = grid.craft(manager)
        self.assertEqual(output.count, 4)
        self.assertEqual(grid.get_slot(0).count, 2)
        self.assertEqual(grid.get_slot(1).count, 1)

    def test_craft_without_recipe_returns_empty_and_preserves_inputs(self):
        grid = CraftingGrid(2, 2)
        grid.set_slot(0, ItemStack(self.wood, 2))
        output = grid.craft(RecipeManager())
        self.assertTrue(output.is_empty)
        self.assertEqual(grid.get_slot(0).count, 2)

    def test_output_is_copied(self):
        grid = CraftingGrid(1, 1)
        output = ItemStack(self.plank, 4)
        manager = RecipeManager()
        manager.register(ShapedRecipe(1, 1, [Ingredient(self.wood)], output))
        output.shrink(1)
        grid.set_slot(0, ItemStack(self.wood, 1))
        crafted = grid.craft(manager)
        self.assertEqual(crafted.count, 4)

    def test_invalid_grid_dimensions(self):
        with self.assertRaises(ValueError):
            CraftingGrid(4, 3)


if __name__ == "__main__":
    unittest.main()
