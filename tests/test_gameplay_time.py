"""Tests for world time and game rules."""
import unittest

from engine.gameplay.time import GameRules, WorldTime
from engine.world import World


class TestWorldTime(unittest.TestCase):
    def test_default_clock(self):
        clock = WorldTime()
        self.assertEqual(clock.total_time, 0)
        self.assertEqual(clock.time_of_day, 6000)
        self.assertTrue(clock.is_day)

    def test_tick_advances_both_clocks(self):
        clock = WorldTime(total_time=10, day_time=23999)
        clock.tick()
        self.assertEqual(clock.total_time, 11)
        self.assertEqual(clock.time_of_day, 0)
        self.assertEqual(clock.day_count, 1)

    def test_daylight_cycle_can_pause_without_stopping_total_time(self):
        clock = WorldTime(total_time=10, day_time=6000)
        clock.tick(daylight_cycle=False)
        self.assertEqual(clock.total_time, 11)
        self.assertEqual(clock.day_time, 6000)

    def test_set_time_of_day_wraps(self):
        clock = WorldTime()
        clock.set_day_time(25000)
        self.assertEqual(clock.time_of_day, 1000)
        self.assertEqual(clock.day_count, 1)

    def test_add_day_time(self):
        clock = WorldTime(day_time=100)
        clock.add_day_time(50)
        self.assertEqual(clock.day_time, 150)
        clock.add_day_time(-1000)
        self.assertEqual(clock.day_time, 0)


class TestWorldIntegration(unittest.TestCase):
    def test_world_tick_advances_clock(self):
        world = World()
        world.tick()
        self.assertEqual(world.world_time.total_time, 1)
        self.assertEqual(world.time_of_day, 6001)

    def test_daylight_cycle_rule_pauses_day_clock(self):
        world = World()
        world.game_rules.set("doDaylightCycle", False)
        world.tick()
        self.assertEqual(world.world_time.total_time, 1)
        self.assertEqual(world.time_of_day, 6000)


class TestGameRules(unittest.TestCase):
    def test_vanilla_defaults(self):
        rules = GameRules()
        self.assertTrue(rules.get_bool("doDaylightCycle"))
        self.assertFalse(rules.get_bool("keepInventory"))
        self.assertEqual(rules.get_int("randomTickSpeed"), 3)

    def test_set_bool_from_string(self):
        rules = GameRules()
        rules.set("doDaylightCycle", "false")
        self.assertFalse(rules.get_bool("doDaylightCycle"))

    def test_set_integer_from_string(self):
        rules = GameRules()
        rules.set("randomTickSpeed", "5")
        self.assertEqual(rules.get_int("randomTickSpeed"), 5)

    def test_type_mismatch_rejected(self):
        rules = GameRules()
        with self.assertRaises(TypeError):
            rules.set("keepInventory", 1)
        with self.assertRaises(ValueError):
            rules.set("randomTickSpeed", "fast")

    def test_custom_rule(self):
        rules = GameRules()
        rules.add_rule("customRule", True)
        self.assertTrue(rules.get_bool("customRule"))
        with self.assertRaises(ValueError):
            rules.add_rule("customRule", False)

    def test_unknown_rule_rejected(self):
        with self.assertRaises(KeyError):
            GameRules().get("notARealRule")


if __name__ == "__main__":
    unittest.main()
