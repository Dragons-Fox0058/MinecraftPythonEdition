"""Smoke tests for the launcher entrypoint imports and build configuration."""
import unittest


class TestLauncher(unittest.TestCase):
    def test_launcher_imports_without_opening_a_window(self):
        import launcher
        self.assertTrue(callable(launcher.Launcher))

    def test_game_entrypoint_is_importable_headlessly(self):
        from engine.app.client import main
        self.assertTrue(callable(main))


if __name__ == "__main__":
    unittest.main()
