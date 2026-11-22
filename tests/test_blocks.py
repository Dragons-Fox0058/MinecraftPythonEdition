"""tests/test_blocks.py — Block system tests."""
import unittest
from engine.blocks import Material, Block, BlockState, BLOCK_REGISTRY
import engine.blocks.vanilla_blocks as VB

class TestMaterials(unittest.TestCase):
    def test_air(self):
        self.assertFalse(Material.AIR.is_solid)
        self.assertFalse(Material.AIR.blocks_movement)
        self.assertTrue(Material.AIR.is_replaceable)

    def test_rock(self):
        self.assertTrue(Material.ROCK.is_solid)
        self.assertTrue(Material.ROCK.blocks_light)
        self.assertTrue(Material.ROCK.blocks_movement)

    def test_water_liquid(self):
        self.assertTrue(Material.WATER.is_liquid)
        self.assertFalse(Material.WATER.blocks_movement)

class TestBlockRegistry(unittest.TestCase):
    def test_air_id_zero(self):
        self.assertIs(BLOCK_REGISTRY.require_id(0), VB.AIR)

    def test_stone_id_one(self):
        self.assertIs(BLOCK_REGISTRY.require_id(1), VB.STONE)
        self.assertIs(BLOCK_REGISTRY.require_name('stone'), VB.STONE)

    def test_grass_id_two(self):
        self.assertIs(BLOCK_REGISTRY.require_id(2), VB.GRASS)

    def test_dirt_id_three(self):
        self.assertIs(BLOCK_REGISTRY.require_id(3), VB.DIRT)

    def test_bedrock(self):
        self.assertIs(BLOCK_REGISTRY.require_id(7), VB.BEDROCK)
        self.assertEqual(VB.BEDROCK.hardness, -1.0)

    def test_water_ids(self):
        self.assertIs(BLOCK_REGISTRY.require_id(8), VB.FLOWING_WATER)
        self.assertIs(BLOCK_REGISTRY.require_id(9), VB.WATER)

    def test_lava_light(self):
        self.assertEqual(VB.LAVA.light_level, 15)

    def test_registry_frozen(self):
        self.assertTrue(BLOCK_REGISTRY._frozen)
        with self.assertRaises(RuntimeError):
            BLOCK_REGISTRY.register(Block('fake', 9999, Material.ROCK))

    def test_count_reasonable(self):
        # We registered a lot of blocks; at least 100.
        self.assertGreaterEqual(len(BLOCK_REGISTRY), 100)

class TestBlockProperties(unittest.TestCase):
    def test_stone_solid(self):
        self.assertTrue(VB.STONE.is_solid())
        self.assertTrue(VB.STONE.is_full_cube())
        self.assertTrue(VB.STONE.is_opaque())

    def test_air_not_solid(self):
        self.assertFalse(VB.AIR.is_solid())
        self.assertFalse(VB.AIR.can_collide())

    def test_glass_transparent(self):
        self.assertFalse(VB.GLASS.is_opaque())
        self.assertEqual(VB.GLASS.opacity, 0)

    def test_leaves_collision(self):
        # Leaves are solid but light passes through
        self.assertTrue(VB.LEAVES.is_solid())
        self.assertFalse(VB.LEAVES.is_opaque())

    def test_torch_light(self):
        self.assertEqual(VB.TORCH.light_level, 14)
        self.assertFalse(VB.TORCH.is_full_cube())

class TestBlockState(unittest.TestCase):
    def test_default_state(self):
        st = VB.STONE.default_state
        self.assertIs(st.block, VB.STONE)
        self.assertEqual(st.properties, ())

    def test_state_equality(self):
        a = BlockState(VB.LOG, ())
        b = BlockState(VB.LOG, ())
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))

    def test_state_inequality(self):
        a = BlockState(VB.LOG, ())
        b = BlockState(VB.STONE, ())
        self.assertNotEqual(a, b)

    def test_with_property(self):
        st = VB.LOG.default_state
        rotated = st.with_property('axis', 'x')
        self.assertEqual(rotated.get('axis'), 'x')
        self.assertEqual(st.get('axis'), None)
        self.assertNotEqual(st, rotated)

    def test_with_property_idempotent(self):
        st = VB.LOG.default_state.with_property('axis', 'x')
        st2 = st.with_property('axis', 'x')
        self.assertIs(st, st2)

if __name__ == '__main__':
    unittest.main()
