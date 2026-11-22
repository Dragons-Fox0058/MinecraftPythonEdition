"""Initial Phase 6 package tests."""
import unittest
import engine.gameplay

class TestGameplayPackage(unittest.TestCase):
    def test_package_imports(self):
        self.assertIsNotNone(engine.gameplay)

if __name__ == "__main__":
    unittest.main()
