"""Tests for hunger, exhaustion, regeneration, and starvation."""
import unittest

from engine.gameplay.health import HungerManager


class DummyLiving:
    def __init__(self, health=20.0, max_health=20.0):
        self.health = health
        self.max_health = max_health
        self.damage_calls = 0

    def heal(self, amount):
        self.health = min(self.max_health, self.health + amount)

    def damage(self, amount):
        self.damage_calls += 1
        self.health = max(0.0, self.health - amount)


class TestHungerManager(unittest.TestCase):
    def test_default_values(self):
        hunger = HungerManager()
        self.assertEqual(hunger.food_level, 20)
        self.assertEqual(hunger.saturation, 5)
        self.assertEqual(hunger.exhaustion, 0)

    def test_exhaustion_consumes_saturation_first(self):
        hunger = HungerManager(food_level=20, saturation=2)
        hunger.add_exhaustion(8)
        hunger.tick(DummyLiving())
        self.assertEqual(hunger.saturation, 1)
        self.assertEqual(hunger.food_level, 20)

    def test_exhaustion_consumes_food_after_saturation(self):
        hunger = HungerManager(food_level=20, saturation=0)
        hunger.add_exhaustion(4.1)
        hunger.tick(DummyLiving())
        self.assertEqual(hunger.food_level, 19)

    def test_exhaustion_is_capped(self):
        hunger = HungerManager()
        hunger.add_exhaustion(100)
        self.assertEqual(hunger.exhaustion, 40)

    def test_eating_restores_food_and_saturation(self):
        hunger = HungerManager(food_level=10, saturation=1)
        hunger.eat(4, 0.8)
        self.assertEqual(hunger.food_level, 14)
        self.assertAlmostEqual(hunger.saturation, 7.4)

    def test_saturation_regeneration(self):
        hunger = HungerManager(food_level=20, saturation=5)
        player = DummyLiving(health=10)
        for _ in range(10):
            hunger.tick(player)
        self.assertEqual(player.health, 11)
        self.assertEqual(hunger.exhaustion, 6)

    def test_unsaturated_regeneration_is_slower(self):
        hunger = HungerManager(food_level=20, saturation=0)
        player = DummyLiving(health=10)
        for _ in range(79):
            hunger.tick(player)
        self.assertEqual(player.health, 10)
        hunger.tick(player)
        self.assertEqual(player.health, 11)

    def test_starvation_normal_difficulty_stops_at_one_health(self):
        hunger = HungerManager(food_level=0, saturation=0)
        player = DummyLiving(health=2)
        for _ in range(160):
            hunger.tick(player, difficulty="normal")
        self.assertEqual(player.health, 1)

    def test_starvation_easy_difficulty_stops_at_half_health(self):
        hunger = HungerManager(food_level=0, saturation=0)
        player = DummyLiving(health=11)
        for _ in range(160):
            hunger.tick(player, difficulty="easy")
        self.assertEqual(player.health, 10)

    def test_starvation_does_not_damage_in_peaceful(self):
        hunger = HungerManager(food_level=0, saturation=0)
        player = DummyLiving(health=20)
        for _ in range(160):
            hunger.tick(player, difficulty="peaceful")
        self.assertEqual(player.health, 20)
        self.assertEqual(player.damage_calls, 0)

    def test_non_finite_exhaustion_rejected(self):
        hunger = HungerManager()
        with self.assertRaises(ValueError):
            hunger.add_exhaustion(float("nan"))

    def test_invalid_difficulty_rejected(self):
        with self.assertRaises(ValueError):
            HungerManager().tick(DummyLiving(), difficulty="impossible")


if __name__ == "__main__":
    unittest.main()
