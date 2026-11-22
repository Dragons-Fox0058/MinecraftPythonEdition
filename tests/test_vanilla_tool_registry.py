"""Tests for source-backed vanilla 1.12.2 tool definitions."""
import unittest
from types import SimpleNamespace

from engine.gameplay.items import Item
from engine.gameplay.vanilla_drops import resolve_vanilla_block_drops
from engine.gameplay.vanilla_tools import (
    VANILLA_TOOL_MATERIALS,
    create_vanilla_tool_items,
    VANILLA_TOOL_ITEM_IDS,
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

    def test_vanilla_tool_item_ids_and_durability(self):
        tools = create_vanilla_tool_items()
        self.assertEqual(set(tools), set(VANILLA_TOOL_ITEM_IDS))
        self.assertEqual(tools["wooden_pickaxe"].item_id, 270)
        self.assertEqual(tools["stone_pickaxe"].item_id, 274)
        self.assertEqual(tools["iron_pickaxe"].item_id, 257)
        self.assertEqual(tools["diamond_pickaxe"].item_id, 278)
        self.assertEqual(tools["golden_pickaxe"].item_id, 285)
        self.assertEqual(tools["diamond_pickaxe"].max_damage, 1561)
        self.assertTrue(all(item.max_stack_size == 1 for item in tools.values()))

    def test_ore_drops_and_fortune_multiplier(self):
        class ScriptedRandom:
            def __init__(self, values):
                self.values = iter(values)

            def randrange(self, stop):
                value = next(self.values)
                if not 0 <= value < stop:
                    raise AssertionError(f"{value} outside randrange({stop})")
                return value

        items = {
            14: Item(14, "minecraft:gold_ore"),
            15: Item(15, "minecraft:iron_ore"),
            16: Item(16, "minecraft:coal_ore"),
            21: Item(21, "minecraft:lapis_ore"),
            56: Item(56, "minecraft:diamond_ore"),
            73: Item(73, "minecraft:redstone_ore"),
            129: Item(129, "minecraft:emerald_ore"),
            153: Item(153, "minecraft:quartz_ore"),
            263: Item(263, "minecraft:coal"),
            264: Item(264, "minecraft:diamond"),
            331: Item(331, "minecraft:redstone"),
            351: Item(351, "minecraft:dye", has_subtypes=True),
            388: Item(388, "minecraft:emerald"),
            406: Item(406, "minecraft:quartz"),
        }

        def block(block_id, name):
            return SimpleNamespace(block_id=block_id, registry_name=name)

        coal = resolve_vanilla_block_drops(
            block(16, "coal_ore"), items, fortune=3,
            rng=ScriptedRandom([4]),
        )[0]
        self.assertEqual((coal.item.item_id, coal.count), (263, 4))

        lapis = resolve_vanilla_block_drops(
            block(21, "lapis_ore"), items, fortune=3,
            rng=ScriptedRandom([4, 3]),
        )[0]
        self.assertEqual((lapis.item.item_id, lapis.count, lapis.metadata), (351, 28, 4))

        redstone = resolve_vanilla_block_drops(
            block(73, "redstone_ore"), items, fortune=3,
            rng=ScriptedRandom([4, 1]),
        )[0]
        self.assertEqual((redstone.item.item_id, redstone.count), (331, 20))

        diamond = resolve_vanilla_block_drops(
            block(56, "diamond_ore"), items, fortune=3,
            rng=ScriptedRandom([4]),
        )[0]
        self.assertEqual((diamond.item.item_id, diamond.count), (264, 4))

        emerald = resolve_vanilla_block_drops(
            block(129, "emerald_ore"), items, fortune=0,
        )[0]
        self.assertEqual((emerald.item.item_id, emerald.count), (388, 1))

        quartz = resolve_vanilla_block_drops(
            block(153, "quartz_ore"), items, fortune=3,
            rng=ScriptedRandom([3]),
        )[0]
        self.assertEqual((quartz.item.item_id, quartz.count), (406, 3))

    def test_iron_and_gold_ores_drop_themselves_even_with_fortune(self):
        items = {
            14: Item(14, "minecraft:gold_ore"),
            15: Item(15, "minecraft:iron_ore"),
        }
        for block_id, name in ((14, "gold_ore"), (15, "iron_ore")):
            drops = resolve_vanilla_block_drops(
                SimpleNamespace(block_id=block_id, registry_name=name),
                items, fortune=3,
            )
            self.assertEqual([(drop.item.item_id, drop.count) for drop in drops],
                             [(block_id, 1)])

    def test_silk_touch_returns_ore_block_instead_of_ore_item(self):
        items = {
            16: Item(16, "minecraft:coal_ore"),
            263: Item(263, "minecraft:coal"),
        }
        drops = resolve_vanilla_block_drops(
            SimpleNamespace(block_id=16, registry_name="coal_ore"),
            items, fortune=3, silk_touch=True,
        )
        self.assertEqual([(drop.item.item_id, drop.count) for drop in drops],
                         [(16, 1)])

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
