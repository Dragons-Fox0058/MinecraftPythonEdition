"""Reference tests for the supported Java 1.12.2 furnace recipe table."""
import unittest

from engine.gameplay.furnace import SmeltingRecipeManager
from engine.gameplay.items import ItemRegistry, ItemStack
from engine.gameplay.vanilla_smelting import (
    register_vanilla_smelting_items, register_vanilla_smelting_recipes,
)


class TestVanillaSmelting(unittest.TestCase):
    def setUp(self):
        self.items = ItemRegistry()
        self.recipes = register_vanilla_smelting_recipes(self.items)

    def test_ore_and_block_recipes(self):
        cases = (
            ("minecraft:iron_ore", 0, "minecraft:iron_ingot", 0, 0.7),
            ("minecraft:gold_ore", 0, "minecraft:gold_ingot", 0, 1.0),
            ("minecraft:diamond_ore", 0, "minecraft:diamond", 0, 1.0),
            ("minecraft:sand", 0, "minecraft:glass", 0, 0.1),
            ("minecraft:cobblestone", 0, "minecraft:stone", 0, 0.1),
            ("minecraft:clay", 0, "minecraft:hardened_clay", 0, 0.35),
            ("minecraft:emerald_ore", 0, "minecraft:emerald", 0, 1.0),
            ("minecraft:coal_ore", 0, "minecraft:coal", 0, 0.1),
            ("minecraft:redstone_ore", 0, "minecraft:redstone", 0, 0.7),
            ("minecraft:quartz_ore", 0, "minecraft:quartz", 0, 0.2),
        )
        for source, meta, output, out_meta, xp in cases:
            with self.subTest(source=source):
                recipe = self.recipes.find_recipe(
                    ItemStack(self.items.require_by_name(source), 1, metadata=meta)
                )
                self.assertIsNotNone(recipe)
                self.assertEqual(recipe.output.item.name, output)
                self.assertEqual(recipe.output.metadata, out_meta)
                self.assertAlmostEqual(recipe.experience, xp)

    def test_food_smelting_recipes(self):
        cases = (
            ("minecraft:porkchop", "minecraft:cooked_porkchop"),
            ("minecraft:beef", "minecraft:cooked_beef"),
            ("minecraft:chicken", "minecraft:cooked_chicken"),
            ("minecraft:rabbit", "minecraft:cooked_rabbit"),
            ("minecraft:mutton", "minecraft:cooked_mutton"),
            ("minecraft:potato", "minecraft:baked_potato"),
        )
        for source, output in cases:
            with self.subTest(source=source):
                recipe = self.recipes.find_recipe(ItemStack(self.items.require_by_name(source), 1))
                self.assertIsNotNone(recipe)
                self.assertEqual(recipe.output.item.name, output)

    def test_metadata_sensitive_recipes(self):
        coal = self.items.require_by_name("minecraft:coal")
        self.assertIsNone(self.recipes.find_recipe(ItemStack(coal, 1, metadata=0)))
        fish = self.items.require_by_name("minecraft:fish")
        self.assertEqual(
            self.recipes.find_recipe(ItemStack(fish, 1, metadata=1)).output.metadata, 1
        )
        self.assertIsNone(self.recipes.find_recipe(ItemStack(fish, 1, metadata=2)))
        sponge = self.items.require_by_name("minecraft:sponge")
        self.assertIsNone(self.recipes.find_recipe(ItemStack(sponge, 1, metadata=0)))
        self.assertEqual(
            self.recipes.find_recipe(ItemStack(sponge, 1, metadata=1)).output.metadata, 0
        )

    def test_all_glazed_terracotta_colors(self):
        clay = self.items.require_by_name("minecraft:stained_hardened_clay")
        for metadata in range(16):
            with self.subTest(metadata=metadata):
                recipe = self.recipes.find_recipe(ItemStack(clay, 1, metadata=metadata))
                self.assertIsNotNone(recipe)
                self.assertTrue(recipe.output.item.name.endswith("_glazed_terracotta"))

    def test_recipe_catalogue_can_use_injected_manager(self):
        manager = SmeltingRecipeManager()
        self.assertIs(register_vanilla_smelting_recipes(self.items, manager), manager)

    def test_catalogue_registration_is_idempotent_for_items(self):
        count = len(self.items)
        register_vanilla_smelting_items(self.items)
        self.assertEqual(len(self.items), count)


if __name__ == "__main__":
    unittest.main()
