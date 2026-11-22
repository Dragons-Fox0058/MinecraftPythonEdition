import unittest

from engine.blocks.registry import GLOBAL


class TestVanillaBlockIDs(unittest.TestCase):
    def test_phase6_block_ids(self):
        expected = {
            36: "piston_extension",
            97: "monster_egg",
            104: "pumpkin_stem",
            105: "melon_stem",
            115: "nether_wart",
            116: "enchanting_table",
            117: "brewing_stand",
            118: "cauldron",
        }

        for block_id, name in expected.items():
            with self.subTest(block_id=block_id):
                block = GLOBAL.by_id(block_id)
                self.assertIsNotNone(block)
                self.assertEqual(block.registry_name, name)

    def test_phase6_block_names(self):
        expected = [
            "piston_extension",
            "monster_egg",
            "pumpkin_stem",
            "melon_stem",
            "nether_wart",
            "enchanting_table",
            "brewing_stand",
            "cauldron",
        ]

        for name in expected:
            with self.subTest(name=name):
                self.assertIsNotNone(GLOBAL.by_name(name))


if __name__ == "__main__":
    unittest.main()
