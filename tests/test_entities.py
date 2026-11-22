"""tests/test_entities.py — Entity physics, collision, pathfinding tests."""
import unittest
from engine.core import BlockPos
from engine.world import World
from engine.entities import (
    Entity, EntityLivingBase, EntityPlayer,
    AITask,
    PathFinder, EntityAITasks, AIWander, JUMP_VELOCITY, GRAVITY,
)


def make_floor(w, y=64, r=2, block=1):
    for x in range(-r, r + 1):
        for z in range(-r, r + 1):
            w.set_block_state_id(BlockPos(x, y, z), block)


class TestEntityBase(unittest.TestCase):
    def test_default_aabb(self):
        w = World()
        e = Entity(w, 0.5, 64, 0.5)
        bb = e.get_entity_bounding_box()
        self.assertAlmostEqual(bb.min_x, 0.2)
        self.assertAlmostEqual(bb.max_x, 0.8)
        self.assertAlmostEqual(bb.min_y, 64.0)
        self.assertAlmostEqual(bb.max_y, 65.8)


class TestGravity(unittest.TestCase):
    def test_falling_accumulates(self):
        w = World()
        e = Entity(w, 0.5, 100, 0.5)
        for _ in range(5):
            e.on_update()
        self.assertLess(e.pos.y, 100.0)
        self.assertLess(e.motion.y, 0.0)

    def test_lands_on_solid_ground(self):
        w = World()
        make_floor(w)
        e = Entity(w, 0.5, 70, 0.5)
        for _ in range(200):
            e.on_update()
            if e.on_ground:
                break
        self.assertTrue(e.on_ground)
        self.assertAlmostEqual(e.pos.y, 65.0, places=2)

    def test_no_ground_in_air(self):
        w = World()
        e = Entity(w, 0.5, 100, 0.5)
        e.on_update()
        self.assertFalse(e.on_ground)


class TestJump(unittest.TestCase):
    def test_jump_requires_ground(self):
        w = World()
        e = EntityLivingBase(w, 0.5, 100, 0.5)
        e.jump()
        self.assertEqual(e.motion.y, 0.0)  # not on ground, jump ignored

    def test_jump_height(self):
        w = World()
        make_floor(w)
        p = EntityPlayer(w, 0.5, 65.0, 0.5)
        p.on_update()
        self.assertTrue(p.on_ground)
        p.jump()
        max_y = p.pos.y
        for _ in range(40):
            p.on_update()
            if p.pos.y > max_y:
                max_y = p.pos.y
        height = max_y - 65.0
        self.assertGreater(height, 1.0)
        self.assertLess(height, 1.6)


class TestCollision(unittest.TestCase):
    def test_wall_stops_movement(self):
        w = World()
        make_floor(w)
        # wall at x=2 spanning y=65..68
        for y in range(65, 69):
            w.set_block_state_id(BlockPos(2, y, 0), 1)
        e = Entity(w, 0.5, 65.0, 0.5)
        e.move(1.0, 0.0, 0.0)
        self.assertLess(e.pos.x + e.width * 0.5, 2.0)

    def test_ceiling_stops_movement(self):
        w = World()
        for x in range(-1, 2):
            for z in range(-1, 2):
                w.set_block_state_id(BlockPos(x, 66, z), 1)
        e = Entity(w, 0.5, 64.0, 0.5)
        e.move(0.0, 5.0, 0.0)
        self.assertLess(e.pos.y + e.height, 67.0)


class TestPlayer(unittest.TestCase):
    def test_player_dimensions(self):
        w = World()
        p = EntityPlayer(w, 0.5, 64, 0.5)
        self.assertEqual(p.width, 0.6)
        self.assertEqual(p.height, 1.8)

    def test_health(self):
        w = World()
        p = EntityPlayer(w, 0.5, 64, 0.5)
        self.assertEqual(p.health, 20.0)
        p.damage(5)
        self.assertEqual(p.health, 15.0)
        p.hurt_time = 0
        p.damage(100)
        self.assertTrue(p.dead)

    def test_invulnerability(self):
        w = World()
        p = EntityPlayer(w, 0.5, 64, 0.5)
        p.damage(5)
        self.assertEqual(p.health, 15.0)
        p.damage(5)
        self.assertEqual(p.health, 15.0)


class TestPathFinder(unittest.TestCase):
    def test_straight_path(self):
        w = World()
        for x in range(-1, 6):
            for z in range(-1, 2):
                w.set_block_state_id(BlockPos(x, 63, z), 1)
        pf = PathFinder()
        path = pf.find_path(w, BlockPos(0, 64, 0), BlockPos(3, 64, 0))
        self.assertIsNotNone(path)
        self.assertEqual(path[0], BlockPos(0, 64, 0))
        self.assertEqual(path[-1], BlockPos(3, 64, 0))

    def test_no_path_when_blocked(self):
        w = World()
        for x in range(-1, 6):
            for z in range(-5, 6):
                w.set_block_state_id(BlockPos(x, 63, z), 1)
        for y in range(64, 75):
            for z in range(-5, 6):
                w.set_block_state_id(BlockPos(2, y, z), 1)
        pf = PathFinder(max_distance=20)
        path = pf.find_path(w, BlockPos(0, 64, 0), BlockPos(4, 64, 0))
        self.assertIsNone(path)


class TestAI(unittest.TestCase):
    def test_ai_tasks_runs(self):
        w = World()
        mob = EntityLivingBase(w, 0.5, 64, 0.5)
        tasks = EntityAITasks()
        tasks.add(AIWander())
        tasks.on_update(mob)
        self.assertTrue(True)


    def test_task_lifecycle_starts_once_and_updates_while_active(self):
        class CountingTask(AITask):
            def __init__(self):
                self.starts = 0
                self.updates = 0
                self.resets = 0
                self.remaining = 2
            def should_execute(self, mob):
                return True
            def should_continue(self, mob):
                return self.remaining > 0
            def start(self, mob):
                self.starts += 1
            def update(self, mob):
                self.updates += 1
                self.remaining -= 1
            def reset(self, mob):
                self.resets += 1

        mob = EntityLivingBase(World(), 0, 64, 0)
        scheduler = EntityAITasks()
        task = CountingTask()
        scheduler.add(task)
        scheduler.on_update(mob)
        self.assertTrue(scheduler.is_running(task))
        scheduler.on_update(mob)
        self.assertEqual(task.starts, 1)
        self.assertEqual(task.updates, 2)
        scheduler.on_update(mob)
        self.assertFalse(scheduler.is_running(task))
        self.assertEqual(task.resets, 1)

    def test_wander_goal_keeps_target_across_ticks(self):
        import random
        mob = EntityLivingBase(World(), 0, 64, 0)
        scheduler = EntityAITasks()
        task = AIWander(rng=random.Random(7))
        scheduler.add(task)
        scheduler.on_update(mob)
        first_target = task.target
        scheduler.on_update(mob)
        self.assertEqual(task.target, first_target)
        self.assertTrue(scheduler.is_running(task))


if __name__ == '__main__':
    unittest.main()
