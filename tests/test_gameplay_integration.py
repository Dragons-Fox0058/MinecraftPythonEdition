"""Cross-system gameplay integration tests."""
import unittest

from engine.core import BlockPos, EnumFacing
from engine.entities import EntityPlayer
from engine.gameplay import Item, ItemStack
from engine.gameplay.player import PlayerController
from engine.world import World
import engine.blocks.vanilla_blocks as VB


class TestGameplayIntegration(unittest.TestCase):
    def test_break_pickup_and_replant_block(self):
        world = World()
        player = EntityPlayer(world, 0.5, 64, 0.5)
        dirt_item = Item(700, "test:dirt")
        controller = PlayerController(
            player,
            block_drop_resolver=lambda block, pos: (
                [ItemStack(dirt_item, 1)] if block is VB.DIRT else []
            ),
        )
        target = BlockPos(2, 64, 0)
        world.set_block_state_id(target, VB.DIRT.block_id)

        broken = controller.break_block(target, dig_speed=1000, can_harvest=True)
        self.assertTrue(broken.broken)
        self.assertTrue(world.is_air(target))
        drops = [entity for entity in world.entities if hasattr(entity, "stack")]
        self.assertEqual(len(drops), 1)

        drops[0].pickup_delay = 0
        self.assertTrue(controller.try_pickup(drops[0]))
        self.assertEqual(controller.inventory.count_item(dirt_item), 1)

        placed = controller.place_block(
            target, EnumFacing.UP,
            lambda item: VB.DIRT if item is dirt_item else None,
        )
        self.assertTrue(placed.placed)
        self.assertEqual(world.get_block_state_id(target), VB.DIRT.block_id)
        self.assertEqual(controller.inventory.count_item(dirt_item), 0)


if __name__ == "__main__":
    unittest.main()
