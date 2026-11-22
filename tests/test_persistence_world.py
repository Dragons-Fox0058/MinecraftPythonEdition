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
            world.spawn_point = BlockPos(-128, 72, 255)
            world.world_time.total_time = 12345
            world.world_time.day_time = 23456
            world.game_rules.set("keepInventory", True)
            world.game_rules.set("randomTickSpeed", 7)
            world.set_packed_block_state(BlockPos(-1, 70, 32), (300 << 4) | 4)
            world.set_packed_block_state(BlockPos(17, 255, -33), (54 << 4) | 2)
            save_world(world, directory)

            loaded = load_world(directory)
            self.assertEqual(loaded.name, world.name)
            self.assertEqual(loaded.seed, world.seed)
            self.assertEqual(loaded.spawn_point, world.spawn_point)
            self.assertEqual(loaded.world_time.total_time, 12345)
            self.assertEqual(loaded.world_time.day_time, 23456)
            self.assertTrue(loaded.game_rules.get_bool("keepInventory"))
            self.assertEqual(loaded.game_rules.get_int("randomTickSpeed"), 7)
            self.assertEqual(loaded.get_packed_block_state(BlockPos(-1, 70, 32)), (300 << 4) | 4)
            self.assertEqual(loaded.get_packed_block_state(BlockPos(17, 255, -33)), (54 << 4) | 2)

    def test_loaded_world_keeps_seeded_chunk_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            world = World("seeded")
            world.seed = 24680
            save_world(world, directory)
            loaded = load_world(directory)
            provider = loaded.chunk_provider
            self.assertEqual(provider.seed, 24680)
            chunk = provider.get_or_create(4, -3)
            self.assertEqual((chunk.pos.x, chunk.pos.z), (4, -3))
            self.assertTrue((chunk.blocks != 0).any())

    def test_missing_level_dat_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(WorldSaveError):
                load_world(directory)

    def test_level_dat_is_gzip_nbt(self):
        with tempfile.TemporaryDirectory() as directory:
            save_world(World("gzip"), directory)
            self.assertEqual((Path(directory) / "level.dat").read_bytes()[:2], b"\x1f\x8b")


    def test_second_save_keeps_previous_level_dat_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            world = World("first")
            save_world(world, directory)
            original = (Path(directory) / "level.dat").read_bytes()
            world.name = "second"
            save_world(world, directory)
            self.assertEqual((Path(directory) / "level.dat_old").read_bytes(), original)
            self.assertEqual(load_world(directory).name, "second")

    def test_chunk_is_not_marked_clean_before_metadata_save_succeeds(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            world = World("failure")
            world.set_block_state_id(BlockPos(0, 64, 0), 1)
            chunk = world.chunk_provider.get_or_create(0, 0)
            with patch("engine.persistence.world._atomic_write", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    save_world(world, directory)
            self.assertTrue(chunk.dirty)


if __name__ == "__main__":
    unittest.main()
