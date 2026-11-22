"""Tests for damage sources and armor reduction."""
import unittest

from engine.gameplay.damage import ArmorDefinition, ArmorRegistry, DamageSource
from engine.gameplay.items import Item, ItemStack


class TestArmorRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = ArmorRegistry()
        self.helmet = Item(3000, "test:helmet", max_stack_size=1, max_damage=100)
        self.chestplate = Item(3001, "test:chestplate", max_stack_size=1, max_damage=100)
        self.registry.register(ArmorDefinition(self.helmet, 3, 0.0))
        self.registry.register(ArmorDefinition(self.chestplate, 8, 2.0))

    def test_damage_reduction_uses_armor_and_toughness(self):
        armor = [ItemStack(self.helmet, 1), ItemStack(self.chestplate, 1)]
        reduced = self.registry.calculate_damage(10.0, armor, DamageSource("mob"))
        self.assertAlmostEqual(reduced, 7.2)

    def test_bypassing_sources_ignore_armor(self):
        armor = [ItemStack(self.chestplate, 1)]
        for source in (
            DamageSource("void", absolute=True),
            DamageSource("magic", magic=True),
            DamageSource("unblockable", bypasses_armor=True),
        ):
            with self.subTest(source=source.name):
                self.assertEqual(
                    self.registry.calculate_damage(7.0, armor, source), 7.0
                )

    def test_armor_wears_down_and_can_break(self):
        stack = ItemStack(self.helmet, 1, damage=98)
        broken = self.registry.damage_armor(
            10.0, [stack], DamageSource("mob")
        )
        self.assertEqual(broken, 1)
        self.assertTrue(stack.is_empty)

    def test_bypassing_source_does_not_damage_armor(self):
        stack = ItemStack(self.chestplate, 1)
        self.registry.damage_armor(
            8.0, [stack], DamageSource("void", absolute=True)
        )
        self.assertEqual(stack.damage, 0)

    def test_invalid_definitions_and_amounts_are_rejected(self):
        with self.assertRaises(ValueError):
            ArmorDefinition(self.helmet, 21)
        with self.assertRaises(ValueError):
            ArmorDefinition(self.helmet, 2, float("nan"))
        with self.assertRaises(ValueError):
            self.registry.calculate_damage(float("inf"), [], DamageSource("mob"))
        with self.assertRaises(ValueError):
            self.registry.damage_armor(-1, [], DamageSource("mob"))


if __name__ == "__main__":
    unittest.main()
