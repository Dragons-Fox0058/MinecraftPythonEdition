"""World metadata and Anvil save/load integration tests."""
import tempfile
import unittest
from pathlib import Path

from engine.core import BlockPos
from engine.persistence.world import load_world, save_world, WorldSaveError
from engine.world.world import World


class TestWorldPersistence(unittest.TestCase):
    def test_world_round_trip_preserves_seed_time_rules_and_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            world = World("Persistence Test")
            world.seed = 987654321
            world.world_time.total_time = 12345
            world.world_time.day_time = 23456
            world.game_rules.set("keepInventory", True)
            world.game_rules.set("randomTickSpeed", 7)
            world.set_block_state_id(BlockPos(-1, 70, 32), (300 << 4) | 4)
            world.set_block_state_id(BlockPos(17, 255, -33), (54 << 4) | 2)
            save_world(world, directory)

            loaded = load_world(directory)
            self.assertEqual(loaded.name, world.name)
            self.assertEqual(loaded.seed, world.seed)
            self.assertEqual(loaded.world_time.total_time, 12345)
            self.assertEqual(loaded.world_time.day_time, 23456)
            self.assertTrue(loaded.game_rules.get_bool("keepInventory"))
            self.assertEqual(loaded.game_rules.get_int("randomTickSpeed"), 7)
            self.assertEqual(loaded.get_block_state_id(BlockPos(-1, 70, 32)), (300 << 4) | 4)
            self.assertEqual(loaded.get_block_state_id(BlockPos(17, 255, -33)), (54 << 4) | 2)

    def test_missing_level_dat_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(WorldSaveError):
                load_world(directory)

    def test_level_dat_is_gzip_nbt(self):
        with tempfile.TemporaryDirectory() as directory:
            save_world(World("gzip"), directory)
            self.assertEqual((Path(directory) / "level.dat").read_bytes()[:2], b"\x1f\x8b")


if __name__ == "__main__":
    unittest.main()
