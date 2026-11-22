"""Reference checks for the Minecraft Java 1.12.2 food catalogue."""
import unittest

from engine.gameplay.health import FoodRegistry
from engine.gameplay.items import ItemRegistry, ItemStack
from engine.gameplay.vanilla_foods import register_vanilla_food_items, register_vanilla_foods


class TestVanillaFoodCatalogue(unittest.TestCase):
    def setUp(self):
        self.items = ItemRegistry()
        self.foods = register_vanilla_foods(self.items)

    def test_food_catalogue_has_expected_item_ids(self):
        self.assertEqual(self.items.require_by_name("minecraft:apple").item_id, 260)
        self.assertEqual(self.items.require_by_name("minecraft:golden_apple").item_id, 322)
        self.assertEqual(self.items.require_by_name("minecraft:fish").item_id, 349)
        self.assertEqual(self.items.require_by_name("minecraft:chorus_fruit").item_id, 432)
        self.assertEqual(self.items.require_by_name("minecraft:beetroot_soup").item_id, 436)

    def test_food_values_match_1122_item_classes(self):
        apple = self.items.require_by_name("minecraft:apple")
        props = self.foods.get(apple)
        self.assertEqual(props.food_points, 4)
        self.assertAlmostEqual(props.saturation_modifier, 0.3)

        steak = self.items.require_by_name("minecraft:cooked_beef")
        props = self.foods.get(steak)
        self.assertEqual(props.food_points, 8)
        self.assertAlmostEqual(props.saturation_modifier, 0.8)

    def test_fish_metadata_variants(self):
        fish = self.items.require_by_name("minecraft:fish")
        self.assertEqual(self.foods.get(fish, 0).food_points, 2)
        self.assertEqual(self.foods.get(fish, 2).food_points, 1)
        self.assertEqual(self.foods.get(fish, 3).food_points, 1)

        cooked = self.items.require_by_name("minecraft:cooked_fish")
        self.assertEqual(self.foods.get(cooked, 0).food_points, 5)
        self.assertEqual(self.foods.get(cooked, 1).food_points, 6)
        self.assertIsNone(self.foods.get(cooked, 2))

    def test_soups_return_bowls(self):
        bowl = self.items.require_by_name("minecraft:bowl")
        for name in ("minecraft:mushroom_stew", "minecraft:rabbit_stew", "minecraft:beetroot_soup"):
            item = self.items.require_by_name(name)
            self.assertEqual(item.max_stack_size, 1)
            self.assertIs(item.container_item, bowl)

    def test_golden_apple_and_chorus_fruit_are_always_edible(self):
        apple = self.items.require_by_name("minecraft:golden_apple")
        chorus = self.items.require_by_name("minecraft:chorus_fruit")
        self.assertTrue(self.foods.get(apple, 0).always_edible)
        self.assertTrue(self.foods.get(apple, 1).always_edible)
        self.assertTrue(self.foods.get(chorus).always_edible)

    def test_food_registration_is_idempotent_for_item_catalogue(self):
        before = len(self.items)
        register_vanilla_food_items(self.items)
        self.assertEqual(len(self.items), before)

    def test_food_registry_can_be_injected(self):
        items = ItemRegistry()
        registry = FoodRegistry()
        returned = register_vanilla_foods(items, registry)
        self.assertIs(returned, registry)
        self.assertEqual(len(registry), 36)


if __name__ == "__main__":
    unittest.main()
