"""Player persistence tests for 1.12.2 NBT inventory slot conventions."""
import unittest
import tempfile
from pathlib import Path
import uuid

from engine.core import read_nbt, write_nbt
from engine.entities.player import EntityPlayer
from engine.gameplay.items import Item, ItemRegistry, ItemStack
from engine.gameplay.player import PlayerController
from engine.gameplay.effects import EffectType, StatusEffect
from engine.persistence.player import player_to_nbt, player_from_nbt, save_player_data, load_player_data
from engine.persistence.world import save_world_player, load_world_player
from engine.world import World


class TestPlayerPersistence(unittest.TestCase):
    def setUp(self):
        self.world = World("players")
        self.items = ItemRegistry()
        self.blocks = Item(1, "minecraft:stone")
        self.sword = Item(267, "minecraft:iron_sword", max_stack_size=1, max_damage=250)
        self.apple = Item(260, "minecraft:apple", has_subtypes=False)
        for item in (self.blocks, self.sword, self.apple):
            self.items.register(item)

    def test_playerdata_file_is_gzip_and_round_trips(self):
        with tempfile.TemporaryDirectory() as directory:
            player = EntityPlayer(self.world, 1, 65, 2, "Disk")
            controller = PlayerController(player)
            controller.inventory.set_slot(0, ItemStack(self.blocks, 12))
            path = Path(directory) / "playerdata" / "test.dat"
            expected = save_player_data(path, player, controller, self.items)
            self.assertEqual(path.read_bytes()[:2], b"\x1f\x8b")
            restored = EntityPlayer(self.world, name="Restored")
            restored_controller = PlayerController(restored)
            actual = load_player_data(path, restored, restored_controller, self.items)
            self.assertEqual(actual, expected)
            self.assertEqual(restored_controller.inventory.slots[0].count, 12)

    def test_world_playerdata_helpers_use_uuid_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            source = EntityPlayer(self.world, 4, 72, -9, "Stored")
            controller = PlayerController(source)
            controller.inventory.set_slot(0, ItemStack(self.blocks, 6))
            player_id = uuid.uuid4()
            saved_id = save_world_player(directory, source, controller, self.items, player_uuid=player_id)
            self.assertEqual(saved_id, player_id)
            path = Path(directory) / "playerdata" / f"{player_id}.dat"
            self.assertTrue(path.is_file())
            restored = EntityPlayer(self.world, name="Loaded")
            restored_controller = PlayerController(restored)
            loaded_id = load_world_player(directory, player_id, restored, restored_controller, self.items)
            self.assertEqual(loaded_id, player_id)
            self.assertEqual(restored_controller.inventory.slots[0].count, 6)

    def test_inventory_armor_offhand_hunger_and_effects_round_trip(self):
        source = EntityPlayer(self.world, 12.5, 70.0, -4.25, "Saver")
        controller = PlayerController(source)
        controller.inventory.set_slot(0, ItemStack(self.blocks, 32, nbt={"display": {"Name": "Stone stack"}}))
        controller.inventory.set_slot(8, ItemStack(self.sword, 1, damage=17))
        controller.inventory.set_armor_slot(0, ItemStack(self.sword, 1, damage=3))
        controller.inventory.set_offhand(ItemStack(self.apple, 5))
        controller.inventory.select_hotbar_slot(8)
        controller.hunger.food_level = 13
        controller.hunger.saturation = 4.5
        controller.hunger.exhaustion = 2.25
        source.health = 16.5
        source.yaw = 90.0
        source.pitch = -10.0
        source.status_effects.add(StatusEffect(EffectType.REGENERATION, 120, 1))
        player_id = uuid.uuid4()

        encoded = write_nbt(player_to_nbt(source, controller, self.items, player_uuid=player_id))
        restored_doc = read_nbt(encoded)
        target = EntityPlayer(self.world, name="Restored")
        target_controller = PlayerController(target)
        restored_id = player_from_nbt(restored_doc, target, target_controller, self.items)

        self.assertEqual(restored_id, player_id)
        self.assertEqual((target.pos.x, target.pos.y, target.pos.z), (12.5, 70.0, -4.25))
        self.assertEqual(target.health, 16.5)
        self.assertEqual(target.yaw, 90.0)
        self.assertEqual(target.pitch, -10.0)
        self.assertEqual(target_controller.inventory.slots[0].count, 32)
        self.assertEqual(target_controller.inventory.slots[0].nbt["display"]["Name"], "Stone stack")
        self.assertEqual(target_controller.inventory.slots[8].damage, 17)
        self.assertEqual(target_controller.inventory.armor[0].damage, 3)
        self.assertEqual(target_controller.inventory.offhand.count, 5)
        self.assertEqual(target_controller.inventory.selected_hotbar_slot, 8)
        self.assertEqual(target_controller.hunger.food_level, 13)
        self.assertEqual(target_controller.hunger.saturation, 4.5)
        self.assertEqual(target_controller.hunger.exhaustion, 2.25)
        effect = target.status_effects.get(EffectType.REGENERATION)
        self.assertEqual((effect.duration, effect.amplifier), (120, 1))


if __name__ == "__main__":
    unittest.main()
