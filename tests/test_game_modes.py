"""Regression tests for the four Java 1.12.2 player game modes."""
import tempfile
import unittest
import uuid

from engine.core import BlockPos, EnumFacing
from engine.entities.player import EntityPlayer
from engine.gameplay import GameMode, Item, ItemRegistry, ItemStack
from engine.gameplay.damage import DamageSource
from engine.gameplay.player import PlayerController
from engine.persistence.world import load_world, save_world, load_world_player, save_world_player
from engine.world import World
import engine.blocks.vanilla_blocks as VB


class TestGameModes(unittest.TestCase):
    def setUp(self):
        self.world = World("game-modes")
        self.player = EntityPlayer(self.world, 0, 64, 0)
        self.controller = PlayerController(self.player)
        self.block_item = Item(900, "test:stone_block")
        self.items = ItemRegistry()
        self.items.register(self.block_item)

    def test_mode_ids_names_and_short_aliases(self):
        expected = (GameMode.SURVIVAL, GameMode.CREATIVE, GameMode.ADVENTURE, GameMode.SPECTATOR)
        for index, mode in enumerate(expected):
            self.assertIs(GameMode.parse(index), mode)
            self.assertIs(GameMode.parse(mode.display_name), mode)
        self.assertIs(GameMode.parse("s"), GameMode.SURVIVAL)
        self.assertIs(GameMode.parse("c"), GameMode.CREATIVE)
        self.assertIs(GameMode.parse("a"), GameMode.ADVENTURE)
        self.assertIs(GameMode.parse("sp"), GameMode.SPECTATOR)
        with self.assertRaises(ValueError):
            GameMode.parse(4)

    def test_gamemode_command_changes_local_player(self):
        self.assertEqual(self.controller.execute_command("/gamemode creative"), "Set own game mode to Creative")
        self.assertIs(self.controller.game_mode, GameMode.CREATIVE)
        self.assertTrue(self.player.is_flying)
        self.assertFalse(self.player.no_clip)
        self.assertEqual(self.controller.execute_command("gamemode 3 @s"), "Set own game mode to Spectator")
        self.assertTrue(self.player.no_clip)
        self.assertEqual(self.controller.execute_command("/gamemode survival"), "Set own game mode to Survival")
        self.assertFalse(self.player.is_flying)
        self.assertFalse(self.player.no_clip)

    def test_command_rejects_invalid_or_other_targets(self):
        self.assertIn("Unknown game mode", self.controller.execute_command("/gamemode 9"))
        self.assertIn("only change your own", self.controller.execute_command("/gamemode creative OtherPlayer"))
        self.assertIn("Usage", self.controller.execute_command("/gamemode"))

    def test_creative_breaks_instantly_without_drops(self):
        pos = BlockPos(2, 64, 2)
        self.world.set_block_state_id(pos, VB.STONE.block_id)
        self.controller.set_game_mode(GameMode.CREATIVE)
        result = self.controller.break_block(pos)
        self.assertTrue(result.broken)
        self.assertEqual(result.progress, 1.0)
        self.assertEqual(result.drops, ())
        self.assertTrue(self.world.is_air(pos))

    def test_creative_placement_does_not_consume_stack(self):
        clicked = BlockPos(0, 64, 0)
        self.world.set_block_state_id(clicked, VB.STONE.block_id)
        self.controller.inventory.set_slot(0, ItemStack(self.block_item, 7))
        self.controller.set_game_mode(GameMode.CREATIVE)
        result = self.controller.place_block(clicked, EnumFacing.UP, lambda item: VB.STONE if item is self.block_item else None)
        self.assertTrue(result.placed)
        self.assertEqual(self.controller.held_item.count, 7)

    def test_adventure_requires_can_destroy_and_can_place_on(self):
        target = BlockPos(1, 64, 1)
        self.world.set_block_state_id(target, VB.STONE.block_id)
        self.controller.set_game_mode(GameMode.ADVENTURE)
        self.assertIsNone(self.controller.break_block(target))
        tool = Item(901, "test:adventure_tool", max_stack_size=1)
        self.controller.inventory.set_slot(0, ItemStack(tool, 1, nbt={"CanDestroy": ["minecraft:stone"]}))
        self.assertTrue(self.controller.break_block(target).broken)

        clicked = BlockPos(3, 64, 3)
        self.world.set_block_state_id(clicked, VB.STONE.block_id)
        self.controller.inventory.set_slot(0, ItemStack(self.block_item, 2))
        self.assertIsNone(self.controller.place_block(clicked, EnumFacing.UP, lambda item: VB.STONE if item is self.block_item else None))
        self.controller.inventory.set_slot(0, ItemStack(self.block_item, 2, nbt={"CanPlaceOn": ["stone"]}))
        result = self.controller.place_block(clicked, EnumFacing.UP, lambda item: VB.STONE if item is self.block_item else None)
        self.assertTrue(result.placed)
        self.assertEqual(self.controller.held_item.count, 1)

    def test_spectator_is_noclip_and_cannot_interact_or_pick_up(self):
        pos = BlockPos(4, 64, 4)
        self.world.set_block_state_id(pos, VB.STONE.block_id)
        self.controller.set_game_mode(GameMode.SPECTATOR)
        self.assertTrue(self.player.no_clip)
        self.assertTrue(self.player.is_flying)
        self.assertIsNone(self.controller.break_block(pos))
        self.assertIsNone(self.controller.place_block(pos, EnumFacing.UP, lambda item: VB.STONE))
        before = self.controller.hunger.tick_count
        self.controller.tick()
        self.assertEqual(self.controller.hunger.tick_count, before)

    def test_creative_and_spectator_ignore_ordinary_damage(self):
        for mode in (GameMode.CREATIVE, GameMode.SPECTATOR):
            self.controller.set_game_mode(mode)
            self.assertFalse(self.controller.damage(5, DamageSource("generic")))
            self.assertEqual(self.player.health, 20)

    def test_player_and_world_game_modes_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            self.world.default_game_mode = GameMode.ADVENTURE
            self.controller.set_game_mode(GameMode.SPECTATOR)
            player_id = uuid.uuid4()
            save_world(self.world, directory)
            save_world_player(directory, self.player, self.controller, self.items, player_uuid=player_id)
            restored_world = load_world(directory)
            self.assertIs(restored_world.default_game_mode, GameMode.ADVENTURE)
            restored_player = EntityPlayer(restored_world, name="Restored")
            restored_controller = PlayerController(restored_player)
            load_world_player(directory, player_id, restored_player, restored_controller, self.items)
            self.assertIs(restored_controller.game_mode, GameMode.SPECTATOR)
            self.assertTrue(restored_player.no_clip)


if __name__ == "__main__":
    unittest.main()
