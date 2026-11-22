"""Tests for vanilla living-entity hurt resistance."""
import unittest

from engine.entities.living import EntityLivingBase
from engine.world import World


class TestLivingDamage(unittest.TestCase):
    def setUp(self):
        self.entity = EntityLivingBase(World())

    def test_first_hit_applies_and_starts_resistance_window(self):
        self.assertTrue(self.entity.damage(5.0))
        self.assertEqual(self.entity.health, 15.0)
        self.assertEqual(self.entity.hurt_time, 10)
        self.assertEqual(self.entity.hurt_resistant_time, 20)

    def test_weaker_or_equal_hit_is_ignored_during_window(self):
        self.assertTrue(self.entity.damage(5.0))
        self.assertFalse(self.entity.damage(5.0))
        self.assertFalse(self.entity.damage(3.0))
        self.assertEqual(self.entity.health, 15.0)

    def test_stronger_hit_only_applies_difference(self):
        self.assertTrue(self.entity.damage(5.0))
        self.assertTrue(self.entity.damage(8.0))
        self.assertEqual(self.entity.health, 12.0)
        self.assertEqual(self.entity.last_damage, 8.0)

    def test_full_damage_applies_after_resistance_window(self):
        self.entity.damage(5.0)
        for _ in range(10):
            self.entity.on_update()
        self.assertEqual(self.entity.hurt_resistant_time, 10)
        self.assertTrue(self.entity.damage(4.0))
        self.assertEqual(self.entity.health, 11.0)

    def test_invalid_damage_is_rejected(self):
        for amount in (-1, float("nan"), float("inf"), True):
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    self.entity.damage(amount)


if __name__ == "__main__":
    unittest.main()
