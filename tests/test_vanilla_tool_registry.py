"""Tests for source-backed vanilla 1.12.2 tool definitions."""
import unittest
from types import SimpleNamespace

from engine.gameplay.items import Item
from engine.gameplay.vanilla_drops import resolve_vanilla_block_drops
from engine.gameplay.vanilla_tools import (
    VANILLA_TOOL_MATERIALS,
    create_vanilla_tool_registry,
)


class TestVanillaToolRegistry(unittest.TestCase):
    def setUp(self):
        self.items = {}
        item_id = 2000
        for material_name, material in VANILLA_TOOL_MATERIALS.items():
            for tool_class in ("pickaxe", "axe", "shovel"):
                name = f"{material_name}_{tool_class}"
                self.items[name] = Item(
                    item_id, f"minecraft:{name}",
                    max_stack_size=1, max_damage=material.durability,
                )
                item_id += 1
        self.registry = create_vanilla_tool_registry(self.items)

    def test_all_five_material_tiers_match_1122_values(self):
        expected = {
            "wooden": (59, 2.0, 0, 15, 0.0),
            "stone": (131, 4.0, 1, 5, 1.0),
            "iron": (250, 6.0, 2, 14, 2.0),
            "diamond": (1561, 8.0, 3, 10, 3.0),
            "golden": (32, 12.0, 0, 22, 0.0),
        }
        actual = {
            name: (
                material.durability, material.efficiency,
                material.harvest_level, material.enchantability,
                material.damage_vs_entity,
            )
            for name, material in VANILLA_TOOL_MATERIALS.items()
        }
        self.assertEqual(actual, expected)

    def test_tool_classes_receive_expected_effective_blocks(self):
        self.assertEqual(
            self.registry.dig_speed(self.items["wooden_pickaxe"], "stone"), 2.0
        )
        self.assertEqual(
            self.registry.dig_speed(self.items["iron_axe"], "log"), 6.0
        )
        self.assertEqual(
            self.registry.dig_speed(self.items["stone_shovel"], "dirt"), 4.0
        )
        self.assertEqual(
            self.registry.dig_speed(self.items["iron_pickaxe"], "dirt"), 1.0
        )

    def test_empty_hand_harvest_rules_match_vanilla(self):
        empty_hand = create_vanilla_tool_registry({})
        # Java 1.12.2 requires a pickaxe for stone and ores, but not dirt.
        self.assertFalse(empty_hand.can_harvest(None, "stone"))
        self.assertFalse(empty_hand.can_harvest(None, "iron_ore"))
        self.assertTrue(empty_hand.can_harvest(None, "dirt"))
        self.assertTrue(empty_hand.can_harvest(None, "sand"))

    def test_stone_drops_cobblestone_and_grass_drops_dirt(self):
        block_items = {
            1: Item(1, "minecraft:stone"),
            3: Item(3, "minecraft:dirt"),
            4: Item(4, "minecraft:cobblestone"),
            20: Item(20, "minecraft:glass"),
        }
        stone = SimpleNamespace(block_id=1, registry_name="stone")
        grass = SimpleNamespace(block_id=2, registry_name="grass")
        stone_drop = resolve_vanilla_block_drops(stone, block_items)
        grass_drop = resolve_vanilla_block_drops(grass, block_items)
        self.assertEqual(stone_drop[0].item.item_id, 4)
        self.assertEqual(grass_drop[0].item.item_id, 3)

    def test_glass_requires_silk_touch_for_a_drop(self):
        glass = SimpleNamespace(block_id=20, registry_name="glass")
        block_items = {20: Item(20, "minecraft:glass")}
        self.assertEqual(resolve_vanilla_block_drops(glass, block_items), [])
        silk_drop = resolve_vanilla_block_drops(
            glass, block_items, silk_touch=True
        )
        self.assertEqual(silk_drop[0].item.item_id, 20)

    def test_gravel_uses_vanilla_flint_chance_formula(self):
        class AlwaysFirst:
            def randrange(self, stop):
                self.asserted_bound = stop
                return 0

        gravel = SimpleNamespace(block_id=13, registry_name="gravel")
        flint = Item(318, "minecraft:flint")
        rng = AlwaysFirst()
        drops = resolve_vanilla_block_drops(
            gravel, {13: Item(13, "minecraft:gravel")},
            flint_item=flint, rng=rng,
        )
        self.assertEqual(rng.asserted_bound, 10)
        self.assertEqual(drops[0].item.item_id, 318)
        self.assertEqual(
            resolve_vanilla_block_drops(
                gravel, {13: Item(13, "minecraft:gravel")},
                flint_item=flint, rng=AlwaysFirst(), fortune=3,
            )[0].item.item_id,
            318,
        )

    def test_vanilla_harvest_levels(self):
        self.assertFalse(
            self.registry.can_harvest(self.items["wooden_pickaxe"], "iron_ore")
        )
        self.assertTrue(
            self.registry.can_harvest(self.items["stone_pickaxe"], "iron_ore")
        )
        self.assertFalse(
            self.registry.can_harvest(self.items["iron_pickaxe"], "obsidian")
        )
        self.assertTrue(
            self.registry.can_harvest(self.items["diamond_pickaxe"], "obsidian")
        )
        self.assertFalse(
            self.registry.can_harvest(self.items["golden_pickaxe"], "diamond_ore")
        )
        self.assertTrue(
            self.registry.can_harvest(self.items["stone_shovel"], "snow_layer")
        )


if __name__ == "__main__":
    unittest.main()
