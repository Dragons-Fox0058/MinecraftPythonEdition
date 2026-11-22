"""Smoke tests for the launcher entrypoint imports and build configuration."""
import unittest


class TestLauncher(unittest.TestCase):
    def test_launcher_imports_without_opening_a_window(self):
        import launcher
        self.assertTrue(callable(launcher.Launcher))

    def test_desktop_player_health_and_death(self):
        from engine.app.client import DesktopPlayer
        from engine.world.world import World
        player = DesktopPlayer(World("test"), 0.5, 64.0, 0.5)
        self.assertEqual(player.health, 20.0)
        self.assertTrue(player.damage(5.0))
        self.assertEqual(player.health, 15.0)
        self.assertTrue(player.heal(2.0))
        self.assertEqual(player.health, 17.0)
        player.damage(100.0)
        self.assertTrue(player.dead)
        self.assertEqual(player.health, 0.0)

    def test_game_entrypoint_is_importable_headlessly(self):
        from engine.app.client import main
        self.assertTrue(callable(main))


if __name__ == "__main__":
    unittest.main()
