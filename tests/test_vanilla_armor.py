"""Tests for the vanilla 1.12.2 armor catalogue factory."""
import unittest

from engine.gameplay.items import Item
from engine.gameplay.vanilla_armor import (
    VANILLA_ARMOR_MATERIALS,
    create_vanilla_armor_registry,
)


SLOT_MULTIPLIERS = {
    "boots": 13,
    "leggings": 15,
    "chestplate": 16,
    "helmet": 11,
}


class TestVanillaArmorRegistry(unittest.TestCase):
    def test_all_material_slot_durability_values(self):
        items = {}
        item_id = 4000
        for material, (base, _points, _toughness) in VANILLA_ARMOR_MATERIALS.items():
            for slot, multiplier in SLOT_MULTIPLIERS.items():
                key = f"{material}_{slot}"
                items[key] = Item(
                    item_id, f"minecraft:{key}", max_stack_size=1,
                    max_damage=base * multiplier,
                )
                item_id += 1

        registry = create_vanilla_armor_registry(items)
        self.assertEqual(sum(registry.get(item) is not None for item in items.values()), 20)

    def test_armor_points_and_toughness_are_source_backed(self):
        diamond_chest = Item(
            4100, "minecraft:diamond_chestplate",
            max_stack_size=1, max_damage=528,
        )
        iron_legs = Item(
            4101, "minecraft:iron_leggings",
            max_stack_size=1, max_damage=225,
        )
        registry = create_vanilla_armor_registry({
            "diamond_chestplate": diamond_chest,
            "iron_leggings": iron_legs,
        })
        self.assertEqual(registry.get(diamond_chest).armor_points, 8)
        self.assertEqual(registry.get(diamond_chest).toughness, 2.0)
        self.assertEqual(registry.get(iron_legs).armor_points, 5)
        self.assertEqual(registry.get(iron_legs).toughness, 0.0)

    def test_unknown_names_and_wrong_durability_are_rejected(self):
        item = Item(4200, "test:wrong", max_stack_size=1, max_damage=1)
        with self.assertRaises(ValueError):
            create_vanilla_armor_registry({"netherite_helmet": item})
        with self.assertRaises(ValueError):
            create_vanilla_armor_registry({"diamond_helmet": item})


if __name__ == "__main__":
    unittest.main()
