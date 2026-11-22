"""Tests for furnace fuel and smelting."""
import unittest

from engine.gameplay import Item, ItemStack
from engine.gameplay.crafting import Ingredient
from engine.gameplay.furnace import FuelRegistry, Furnace, SmeltingRecipe, SmeltingRecipeManager


class TestFurnace(unittest.TestCase):
    def setUp(self):
        self.ore = Item(1, "test:ore")
        self.ingot = Item(2, "test:ingot")
        self.coal = Item(3, "test:coal")
        self.fuels = FuelRegistry()
        self.fuels.register(self.coal, 1600)
        self.recipes = SmeltingRecipeManager()
        self.recipe = self.recipes.register(
            SmeltingRecipe(Ingredient(self.ore), ItemStack(self.ingot, 1), experience=0.7)
        )
        self.furnace = Furnace(self.fuels, self.recipes, cook_time=3)

    def test_non_finite_experience_rejected(self):
        with self.assertRaises(ValueError):
            SmeltingRecipe(Ingredient(self.ore), ItemStack(self.ingot, 1), experience=float("nan"))

    def test_fuel_registry(self):
        self.assertEqual(self.fuels.get_burn_time(ItemStack(self.coal, 1)), 1600)
        self.assertEqual(self.fuels.get_burn_time(ItemStack(self.ore, 1)), 0)
        self.assertEqual(self.fuels.get_burn_time(ItemStack.empty()), 0)

    def test_fuel_validation(self):
        with self.assertRaises(ValueError):
            self.fuels.register(self.coal, 0)

    def test_smelting_progress_and_output(self):
        self.furnace.input = ItemStack(self.ore, 2)
        self.furnace.fuel = ItemStack(self.coal, 1)
        self.assertFalse(self.furnace.update())
        self.assertTrue(self.furnace.is_burning)
        self.assertFalse(self.furnace.update())
        self.assertTrue(self.furnace.update())
        self.assertEqual(self.furnace.output.count, 1)
        self.assertEqual(self.furnace.input.count, 1)

    def test_no_fuel_means_no_progress(self):
        self.furnace.input = ItemStack(self.ore, 1)
        self.assertFalse(self.furnace.update())
        self.assertEqual(self.furnace.cook_time, 0)
        self.assertEqual(self.furnace.input.count, 1)

    def test_incompatible_output_blocks_smelting(self):
        other = Item(4, "test:other")
        self.furnace.input = ItemStack(self.ore, 1)
        self.furnace.output = ItemStack(other, 1)
        self.furnace.fuel = ItemStack(self.coal, 1)
        self.assertFalse(self.furnace.update())
        self.assertFalse(self.furnace.is_burning)

    def test_output_stack_limit(self):
        self.furnace.input = ItemStack(self.ore, 1)
        self.furnace.output = ItemStack(self.ingot, 64)
        self.assertFalse(self.furnace.can_smelt())

    def test_input_consumed_only_when_smelted(self):
        self.furnace.input = ItemStack(self.ore, 1)
        self.furnace.fuel = ItemStack(self.coal, 1)
        for _ in range(2):
            self.furnace.update()
        self.assertEqual(self.furnace.input.count, 1)
        self.furnace.update()
        self.assertTrue(self.furnace.input.is_empty)


if __name__ == "__main__":
    unittest.main()
