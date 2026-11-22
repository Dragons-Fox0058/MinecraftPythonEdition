"""Reference tests for Minecraft Java 1.12.2 furnace fuels."""
import unittest

from engine.gameplay.furnace import FuelRegistry
from engine.gameplay.items import ItemRegistry, ItemStack
from engine.gameplay.vanilla_fuels import register_vanilla_fuel_items, register_vanilla_fuels


class TestVanillaFuels(unittest.TestCase):
    def setUp(self):
        self.items = ItemRegistry()
        self.fuels = register_vanilla_fuels(self.items)

    def test_known_fuel_durations(self):
        cases = (
            ("minecraft:coal_block", 16000, 0),
            ("minecraft:coal", 1600, 0),
            ("minecraft:coal", 1600, 1),
            ("minecraft:lava_bucket", 20000, 0),
            ("minecraft:blaze_rod", 2400, 0),
            ("minecraft:planks", 300, 0),
            ("minecraft:wooden_slab", 150, 0),
            ("minecraft:wool", 100, 0),
            ("minecraft:carpet", 67, 0),
            ("minecraft:ladder", 300, 0),
            ("minecraft:stick", 100, 0),
            ("minecraft:sign", 200, 0),
            ("minecraft:boat", 400, 0),
        )
        for name, expected, metadata in cases:
            with self.subTest(name=name, metadata=metadata):
                item = self.items.require_by_name(name)
                self.assertEqual(self.fuels.get_burn_time(ItemStack(item, 1, metadata=metadata)), expected)

    def test_lava_bucket_returns_empty_bucket(self):
        bucket = self.items.require_by_name("minecraft:bucket")
        lava_bucket = self.items.require_by_name("minecraft:lava_bucket")
        self.assertIs(lava_bucket.container_item, bucket)
        self.assertEqual(lava_bucket.max_stack_size, 1)

    def test_non_fuel_returns_zero(self):
        coal = self.items.require_by_name("minecraft:coal")
        self.assertEqual(self.fuels.get_burn_time(ItemStack(coal, 1, metadata=2)), 0)

    def test_catalogue_registration_is_idempotent(self):
        count = len(self.items)
        register_vanilla_fuel_items(self.items)
        self.assertEqual(len(self.items), count)

    def test_injected_fuel_registry_is_used(self):
        registry = FuelRegistry()
        self.assertIs(register_vanilla_fuels(self.items, registry), registry)


if __name__ == "__main__":
    unittest.main()
