"""Tests for vanilla 1.12.2 tool crafting recipes."""
import unittest

from engine.gameplay.crafting import CraftingGrid
from engine.gameplay.items import Item, ItemStack
from engine.gameplay.vanilla_tools import create_vanilla_tool_items
from engine.gameplay.vanilla_recipes import create_vanilla_tool_recipes


class TestVanillaToolRecipes(unittest.TestCase):
    def setUp(self):
        self.tools = create_vanilla_tool_items()
        self.items = {
            "planks": Item(5, "minecraft:planks", has_subtypes=True),
            "cobblestone": Item(4, "minecraft:cobblestone"),
            "iron_ingot": Item(265, "minecraft:iron_ingot"),
            "diamond": Item(264, "minecraft:diamond"),
            "gold_ingot": Item(266, "minecraft:gold_ingot"),
            "stick": Item(280, "minecraft:stick"),
            "log": Item(17, "minecraft:log", has_subtypes=True),
            "crafting_table": Item(58, "minecraft:crafting_table"),
        }
        self.recipes = create_vanilla_tool_recipes(self.tools, self.items)

    def test_all_fifteen_tool_recipes_registered(self):
        self.assertEqual(len(self.recipes), 18)

    def test_player_2x2_grid_crafts_planks_sticks_and_crafting_table(self):
        grid = CraftingGrid(2, 2)
        grid.set_slot(0, ItemStack(self.items["log"], 1, metadata=3))
        planks = grid.craft(self.recipes)
        self.assertIs(planks.item, self.items["planks"])
        self.assertEqual(planks.count, 4)

        grid.set_slot(0, ItemStack(self.items["planks"], 1, metadata=3))
        grid.set_slot(2, ItemStack(self.items["planks"], 1, metadata=3))
        sticks = grid.craft(self.recipes)
        self.assertIs(sticks.item, self.items["stick"])
        self.assertEqual(sticks.count, 4)

        for slot in range(4):
            grid.set_slot(slot, ItemStack(self.items["planks"], 1, metadata=3))
        table = grid.craft(self.recipes)
        self.assertIs(table.item, self.items["crafting_table"])
        self.assertEqual(table.count, 1)

    def test_player_2x2_grid_crafts_planks_sticks_and_crafting_table(self):
        grid = CraftingGrid(2, 2)
        grid.set_slot(0, ItemStack(self.items["log"], 1, metadata=3))
        planks = grid.craft(self.recipes)
        self.assertIs(planks.item, self.items["planks"])
        self.assertEqual(planks.count, 4)

        grid.set_slot(0, ItemStack(self.items["planks"], 1, metadata=3))
        grid.set_slot(2, ItemStack(self.items["planks"], 1, metadata=3))
        sticks = grid.craft(self.recipes)
        self.assertIs(sticks.item, self.items["stick"])
        self.assertEqual(sticks.count, 4)

        for slot in range(4):
            grid.set_slot(slot, ItemStack(self.items["planks"], 1, metadata=3))
        table = grid.craft(self.recipes)
        self.assertIs(table.item, self.items["crafting_table"])
        self.assertEqual(table.count, 1)

    def test_player_2x2_grid_crafts_planks_sticks_and_crafting_table(self):
        grid = CraftingGrid(2, 2)
        grid.set_slot(0, ItemStack(self.items["log"], 1, metadata=3))
        planks = grid.craft(self.recipes)
        self.assertIs(planks.item, self.items["planks"])
        self.assertEqual(planks.count, 4)

        grid.set_slot(0, ItemStack(self.items["planks"], 1, metadata=3))
        grid.set_slot(2, ItemStack(self.items["planks"], 1, metadata=3))
        sticks = grid.craft(self.recipes)
        self.assertIs(sticks.item, self.items["stick"])
        self.assertEqual(sticks.count, 4)

        for slot in range(4):
            grid.set_slot(slot, ItemStack(self.items["planks"], 1, metadata=3))
        table = grid.craft(self.recipes)
        self.assertIs(table.item, self.items["crafting_table"])
        self.assertEqual(table.count, 1)

    def test_crafts_wooden_pickaxe_and_consumes_exact_inputs(self):
        grid = CraftingGrid(3, 3)
        for slot in (0, 1, 2):
            grid.set_slot(slot, ItemStack(self.items["planks"], 1, metadata=2))
        grid.set_slot(4, ItemStack(self.items["stick"], 1))
        grid.set_slot(7, ItemStack(self.items["stick"], 1))
        recipe = self.recipes.find_matching_recipe(grid)
        self.assertIsNotNone(recipe)
        self.assertIs(recipe.output.item, self.tools["wooden_pickaxe"])
        result = grid.craft(self.recipes)
        self.assertIs(result.item, self.tools["wooden_pickaxe"])
        self.assertTrue(all(stack.is_empty for stack in grid.slots))

    def test_crafts_iron_axe_and_supports_mirrored_pattern(self):
        grid = CraftingGrid(3, 3)
        grid.set_slot(1, ItemStack(self.items["iron_ingot"], 1))
        grid.set_slot(2, ItemStack(self.items["iron_ingot"], 1))
        grid.set_slot(4, ItemStack(self.items["stick"], 1))
        grid.set_slot(5, ItemStack(self.items["iron_ingot"], 1))
        grid.set_slot(7, ItemStack(self.items["stick"], 1))
        recipe = self.recipes.find_matching_recipe(grid)
        self.assertIsNotNone(recipe)
        self.assertIs(recipe.output.item, self.tools["iron_axe"])

    def test_crafting_does_not_consume_when_no_recipe_matches(self):
        grid = CraftingGrid(3, 3)
        grid.set_slot(0, ItemStack(self.items["diamond"], 1))
        self.assertTrue(grid.craft(self.recipes).is_empty)
        self.assertEqual(grid.get_slot(0).count, 1)


if __name__ == "__main__":
    unittest.main()
