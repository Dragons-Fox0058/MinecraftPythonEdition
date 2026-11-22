"""Tests for food items and hunger consumption."""
import unittest

from engine.gameplay.health import FoodProperties, FoodRegistry, HungerManager
from engine.gameplay.items import Item, ItemStack


class TestFoodConsumption(unittest.TestCase):
    def setUp(self):
        self.apple = Item(1, "minecraft:apple")
        self.golden_apple = Item(2, "minecraft:golden_apple")
        self.foods = FoodRegistry()
        self.foods.register(self.apple, FoodProperties(4, 0.3))
        self.foods.register(self.golden_apple, FoodProperties(4, 1.2, always_edible=True))

    def test_consume_food_restores_hunger_and_saturation(self):
        hunger = HungerManager(food_level=10, saturation=1)
        stack = ItemStack(self.apple, 2)
        self.assertTrue(hunger.consume(stack, self.foods))
        self.assertEqual(hunger.food_level, 14)
        self.assertAlmostEqual(hunger.saturation, 3.4)
        self.assertEqual(stack.count, 1)

    def test_regular_food_cannot_be_eaten_when_full(self):
        hunger = HungerManager()
        stack = ItemStack(self.apple, 1)
        self.assertFalse(hunger.consume(stack, self.foods))
        self.assertEqual(stack.count, 1)

    def test_always_edible_food_can_be_eaten_when_full(self):
        hunger = HungerManager()
        stack = ItemStack(self.golden_apple, 1)
        self.assertTrue(hunger.consume(stack, self.foods))
        self.assertEqual(stack.count, 0)
        self.assertEqual(hunger.food_level, 20)

    def test_soup_consumption_replaces_held_item_with_bowl(self):
        bowl = Item(10, "test:bowl", max_stack_size=64)
        soup = Item(11, "test:soup", max_stack_size=1, container_item=bowl)
        foods = FoodRegistry()
        foods.register(soup, FoodProperties(6, 1.2))
        hunger = HungerManager(food_level=10)
        stack = ItemStack(soup, 1)
        self.assertTrue(hunger.consume(stack, foods))
        self.assertIs(stack.item, bowl)
        self.assertEqual(stack.count, 1)

    def test_unregistered_item_is_not_food(self):
        hunger = HungerManager(food_level=10)
        stick = Item(3, "minecraft:stick")
        self.assertFalse(hunger.consume(ItemStack(stick, 1), self.foods))

    def test_food_registry_supports_metadata_variants(self):
        fish = Item(4, "minecraft:fish", has_subtypes=True)
        registry = FoodRegistry()
        registry.register(fish, FoodProperties(2, 0.2), metadata=0)
        registry.register(fish, FoodProperties(5, 1.2), metadata=4)
        self.assertEqual(registry.get(fish, 0).food_points, 2)
        self.assertEqual(registry.get(fish, 4).food_points, 5)
        self.assertIsNone(registry.get(fish, 1))

    def test_food_registry_rejects_duplicates(self):
        with self.assertRaises(ValueError):
            self.foods.register(self.apple, FoodProperties(1, 0.1))

    def test_food_properties_validate_values(self):
        with self.assertRaises(ValueError):
            FoodProperties(21, 0.5)
        with self.assertRaises(ValueError):
            FoodProperties(2, float("nan"))


if __name__ == "__main__":
    unittest.main()
