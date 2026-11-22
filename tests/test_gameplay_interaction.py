"""Tests for block ray tracing."""
import unittest

from engine.core import BlockPos, EnumFacing, Vec3d
from engine.gameplay.interaction import InteractionManager
from engine.world import World
import engine.blocks.vanilla_blocks as VB


class TestInteractionManager(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.interaction = InteractionManager(self.world)

    def test_ray_hits_block_in_front(self):
        self.world.set_block_state_id(BlockPos(3, 64, 0), VB.STONE.block_id)
        hit = self.interaction.ray_trace_blocks(Vec3d(0.5, 64.5, 0.5), Vec3d(1, 0, 0))
        self.assertIsNotNone(hit)
        self.assertEqual(hit.pos, BlockPos(3, 64, 0))
        self.assertEqual(hit.side_hit, EnumFacing.WEST)
        self.assertAlmostEqual(hit.distance, 2.5)

    def test_ray_hits_negative_direction(self):
        self.world.set_block_state_id(BlockPos(-2, 64, 0), VB.STONE.block_id)
        hit = self.interaction.ray_trace_blocks(Vec3d(0.5, 64.5, 0.5), Vec3d(-1, 0, 0))
        self.assertEqual(hit.pos, BlockPos(-2, 64, 0))
        self.assertEqual(hit.side_hit, EnumFacing.EAST)

    def test_max_distance_limits_ray(self):
        self.world.set_block_state_id(BlockPos(3, 64, 0), VB.STONE.block_id)
        hit = self.interaction.ray_trace_blocks(
            Vec3d(0.5, 64.5, 0.5), Vec3d(1, 0, 0), max_distance=2
        )
        self.assertIsNone(hit)

    def test_zero_direction_returns_no_hit(self):
        self.world.set_block_state_id(BlockPos(1, 64, 0), VB.STONE.block_id)
        self.assertIsNone(self.interaction.ray_trace_blocks(
            Vec3d(0.5, 64.5, 0.5), Vec3d(0, 0, 0)
        ))

    def test_start_inside_block(self):
        pos = BlockPos(0, 64, 0)
        self.world.set_block_state_id(pos, VB.STONE.block_id)
        hit = self.interaction.ray_trace_blocks(Vec3d(0.5, 64.5, 0.5), Vec3d(1, 0, 0))
        self.assertEqual(hit.pos, pos)
        self.assertIsNone(hit.side_hit)
        self.assertEqual(hit.distance, 0)

    def test_invalid_distance_rejected(self):
        with self.assertRaises(ValueError):
            self.interaction.ray_trace_blocks(Vec3d(0, 0, 0), Vec3d(1, 0, 0), -1)


if __name__ == "__main__":
    unittest.main()
