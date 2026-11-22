"""Tests for the integrated player gameplay controller."""
import unittest

from engine.core import BlockPos, EnumFacing
from engine.entities import EntityPlayer
from engine.gameplay import (
    ArmorDefinition, ArmorRegistry, DamageSource,
    FoodProperties, FoodRegistry, Item, ItemRegistry, ItemStack,
)
from engine.gameplay.crafting import CraftingGrid
from engine.gameplay.vanilla_food_recipes import register_vanilla_food_recipes
from engine.gameplay.player import PlayerController
from engine.world import World
import engine.blocks.vanilla_blocks as VB


class TestPlayerController(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.player = EntityPlayer(self.world, 0, 64, 0)
        self.controller = PlayerController(self.player)
        self.stone_item = Item(500, "test:stone_block")
        self.apple = Item(501, "test:apple")
        self.controller.food_registry.register(self.apple, FoodProperties(4, 0.3))

    def test_player_damage_uses_equipped_armor(self):
        armor_item = Item(700, "test:chestplate", max_stack_size=1, max_damage=100)
        armor_registry = ArmorRegistry()
        armor_registry.register(ArmorDefinition(armor_item, 8, 2.0))
        player = EntityPlayer(self.world, 4, 64, 4)
        controller = PlayerController(player, armor_registry=armor_registry)
        controller.inventory.set_armor_slot(1, ItemStack(armor_item, 1))
        self.assertTrue(controller.damage(10.0, DamageSource("mob")))
        self.assertAlmostEqual(player.health, 11.6)
        self.assertEqual(controller.inventory.armor[1].damage, 3)

    def test_unblockable_player_damage_bypasses_armor_and_wear(self):
        armor_item = Item(701, "test:helmet", max_stack_size=1, max_damage=100)
        armor_registry = ArmorRegistry()
        armor_registry.register(ArmorDefinition(armor_item, 3))
        player = EntityPlayer(self.world, 5, 64, 5)
        controller = PlayerController(player, armor_registry=armor_registry)
        controller.inventory.set_armor_slot(0, ItemStack(armor_item, 1))
        self.assertTrue(controller.damage(5.0, DamageSource("void", absolute=True)))
        self.assertEqual(player.health, 15.0)
        self.assertEqual(controller.inventory.armor[0].damage, 0)

    def test_player_damage_rejects_invalid_amounts(self):
        for amount in (-1, float("nan"), float("inf"), True):
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    self.controller.damage(amount)

    def test_controller_attaches_player_components(self):
        self.assertIs(self.player.inventory, self.controller.inventory)
        self.assertIs(self.player.hunger, self.controller.hunger)
        self.assertIn(self.player, self.world.entities)

    def test_hotbar_and_held_item(self):
        self.controller.inventory.set_slot(1, ItemStack(self.stone_item, 5))
        self.controller.select_hotbar_slot(1)
        self.assertEqual(self.controller.held_item.count, 5)

    def test_world_tick_updates_player_hunger(self):
        self.controller.hunger.food_level = 0
        self.controller.hunger.saturation = 0
        self.player.health = 2
        for _ in range(80):
            self.world.tick()
        self.assertEqual(self.world.world_time.total_time, 80)
        self.assertLess(self.player.health, 2)

    def test_block_breaking_is_exposed(self):
        pos = BlockPos(0, 64, 1)
        self.world.set_block_state_id(pos, VB.TALLGRASS.block_id)
        result = self.controller.break_block(pos)
        self.assertTrue(result.broken)

    def test_block_placement_uses_held_item(self):
        self.controller.inventory.set_slot(0, ItemStack(self.stone_item, 2))
        result = self.controller.place_block(
            BlockPos(2, 64, 2), EnumFacing.UP,
            lambda item: VB.STONE if item is self.stone_item else None,
        )
        self.assertTrue(result.placed)
        self.assertEqual(self.controller.held_item.count, 1)

    def test_explicit_empty_food_registry_is_preserved(self):
        registry = FoodRegistry()
        player = EntityPlayer(self.world, 4, 64, 4)
        controller = PlayerController(player, food_registry=registry)
        self.assertIs(controller.food_registry, registry)

    def test_consume_food_from_selected_hotbar_slot(self):
        self.controller.hunger.food_level = 10
        self.controller.inventory.set_slot(0, ItemStack(self.apple, 2))
        self.assertTrue(self.controller.consume_food())
        self.assertEqual(self.controller.hunger.food_level, 14)
        self.assertEqual(self.controller.held_item.count, 1)

    def test_craft_to_inventory_collects_food_result(self):
        registry = ItemRegistry()
        recipes = register_vanilla_food_recipes(registry)
        wheat = registry.require_by_name("minecraft:wheat")
        grid = CraftingGrid(3, 3)
        for slot in range(3):
            grid.set_slot(slot, ItemStack(wheat, 1))
        result = self.controller.craft_to_inventory(grid, recipes)
        self.assertEqual(result.item.name, "minecraft:bread")
        self.assertEqual(self.controller.inventory.count_item(result.item), 1)
        self.assertTrue(all(grid.get_slot(i).is_empty for i in range(3)))

    def test_craft_to_inventory_drops_output_when_inventory_full(self):
        registry = __import__("engine.gameplay.items", fromlist=["ItemRegistry"]).ItemRegistry()
        recipes = register_vanilla_food_recipes(registry)
        wheat = registry.require_by_name("minecraft:wheat")
        bread = registry.require_by_name("minecraft:bread")
        for slot in range(36):
            self.controller.inventory.set_slot(slot, ItemStack(self.stone_item, 64))
        grid = CraftingGrid(3, 3)
        for slot in range(3):
            grid.set_slot(slot, ItemStack(wheat, 1))
        self.controller.craft_to_inventory(grid, recipes)
        drops = [entity for entity in self.world.entities if hasattr(entity, "stack")]
        self.assertEqual(sum(e.stack.count for e in drops if e.stack.item is bread), 1)

    def test_consuming_stew_returns_bowl_to_inventory(self):
        bowl = Item(502, "test:bowl")
        stew = Item(503, "test:stew", max_stack_size=1, container_item=bowl)
        self.controller.food_registry.register(stew, FoodProperties(6, 1.2))
        self.controller.hunger.food_level = 10
        self.controller.inventory.set_slot(0, ItemStack(stew, 1))
        self.assertTrue(self.controller.consume_food())
        self.assertIs(self.controller.held_item.item, bowl)
        self.assertEqual(self.controller.inventory.count_item(bowl), 1)

    def test_death_drops_inventory_and_equipment(self):
        self.controller.inventory.set_slot(0, ItemStack(self.stone_item, 5))
        self.controller.inventory.set_armor_slot(0, ItemStack(self.stone_item, 1))
        self.controller.inventory.set_offhand(ItemStack(self.stone_item, 2))
        self.player.dead = True
        self.world.tick()
        self.assertNotIn(self.player, self.world.entities)
        item_entities = [e for e in self.world.entities if hasattr(e, "stack")]
        self.assertEqual(sum(e.stack.count for e in item_entities), 8)
        self.assertTrue(self.controller.inventory.get_slot(0).is_empty)
        self.assertTrue(self.controller.inventory.armor[0].is_empty)
        self.assertTrue(self.controller.inventory.offhand.is_empty)

    def test_keep_inventory_prevents_death_drops(self):
        self.controller.inventory.set_slot(0, ItemStack(self.stone_item, 5))
        self.world.game_rules.set("keepInventory", True)
        self.player.dead = True
        self.world.tick()
        self.assertTrue(self.controller.inventory.get_slot(0).count == 5)
        self.assertFalse(any(hasattr(e, "stack") for e in self.world.entities))

    def test_do_entity_drops_disables_player_death_drops(self):
        self.controller.inventory.set_slot(0, ItemStack(self.stone_item, 5))
        self.world.game_rules.set("doEntityDrops", False)
        self.player.dead = True
        self.world.tick()
        self.assertEqual(self.controller.inventory.get_slot(0).count, 5)
        self.assertFalse(any(hasattr(e, "stack") for e in self.world.entities))

    def test_death_drops_are_processed_only_once(self):
        self.controller.inventory.set_slot(0, ItemStack(self.stone_item, 5))
        self.player.dead = True
        first = self.controller.on_death()
        second = self.controller.on_death()
        self.assertEqual(len(first), 1)
        self.assertEqual(second, ())

    def test_drop_and_pickup(self):
        source = ItemStack(self.stone_item, 3)
        drop = self.controller.drop_item(source)
        self.assertTrue(source.is_empty)
        self.assertIsNotNone(drop)
        self.assertTrue(drop.stack.count == 3)
        drop.pickup_delay = 0
        self.assertTrue(self.controller.try_pickup(drop))
        self.assertEqual(self.controller.inventory.count_item(self.stone_item), 3)


if __name__ == "__main__":
    unittest.main()
