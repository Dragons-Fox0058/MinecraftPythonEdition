"""Tests for block breaking progress."""
import unittest

from engine.core import BlockPos
from engine.gameplay.breaking import BlockBreaking
from engine.world import World
import engine.blocks.vanilla_blocks as VB


class TestBlockBreaking(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.breaking = BlockBreaking(self.world)
        self.pos = BlockPos(0, 64, 0)

    def test_relative_hardness_matches_vanilla_divisors(self):
        self.assertAlmostEqual(BlockBreaking.relative_hardness(1.5, 1.0, True), 1 / 45)
        self.assertAlmostEqual(BlockBreaking.relative_hardness(1.5, 1.0, False), 1 / 150)

    def test_unbreakable_block_never_progresses(self):
        self.assertEqual(BlockBreaking.relative_hardness(-1, 10, True), 0)

    def test_zero_hardness_is_instant(self):
        self.assertEqual(BlockBreaking.relative_hardness(0, 1, False), 1)

    def test_negative_speed_rejected(self):
        with self.assertRaises(ValueError):
            BlockBreaking.relative_hardness(1, -1, True)

    def test_damage_accumulates_until_block_breaks(self):
        self.world.set_block_state_id(self.pos, VB.DIRT.block_id)
        result = self.breaking.damage_block(self.pos, dig_speed=1, can_harvest=True)
        self.assertFalse(result.broken)
        self.assertGreater(result.progress, 0)
        for _ in range(100):
            result = self.breaking.damage_block(self.pos, dig_speed=100, can_harvest=True)
            if result.broken:
                break
        self.assertTrue(result.broken)
        self.assertEqual(result.block_id, VB.DIRT.block_id)
        self.assertTrue(self.world.is_air(self.pos))
        self.assertIsNone(self.breaking.target)

    def test_hardness_zero_block_breaks_immediately(self):
        self.world.set_block_state_id(self.pos, VB.TALLGRASS.block_id)
        result = self.breaking.damage_block(self.pos)
        self.assertTrue(result.broken)
        self.assertTrue(self.world.is_air(self.pos))

    def test_unbreakable_bedrock_does_not_break(self):
        self.world.set_block_state_id(self.pos, VB.BEDROCK.block_id)
        result = self.breaking.damage_block(self.pos, dig_speed=10000, can_harvest=True)
        self.assertFalse(result.broken)
        self.assertEqual(self.world.get_block_state_id(self.pos), VB.BEDROCK.block_id)

    def test_changing_target_resets_progress(self):
        other = BlockPos(1, 64, 0)
        self.world.set_block_state_id(self.pos, VB.STONE.block_id)
        self.world.set_block_state_id(other, VB.STONE.block_id)
        first = self.breaking.damage_block(self.pos, dig_speed=1, can_harvest=True)
        second = self.breaking.damage_block(other, dig_speed=1, can_harvest=True)
        self.assertGreater(first.progress, 0)
        self.assertEqual(second.progress, first.progress)

    def test_air_target_resets_progress(self):
        self.world.set_block_state_id(self.pos, VB.DIRT.block_id)
        self.breaking.damage_block(self.pos, dig_speed=1, can_harvest=True)
        result = self.breaking.damage_block(BlockPos(3, 64, 0))
        self.assertFalse(result.broken)
        self.assertIsNone(self.breaking.target)
        self.assertEqual(self.breaking.progress, 0)


if __name__ == "__main__":
    unittest.main()
