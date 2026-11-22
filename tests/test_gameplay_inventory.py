"""Tests for the Phase 6 player inventory and hotbar."""
import unittest

from engine.gameplay import Inventory, Item, ItemStack


class TestInventory(unittest.TestCase):
    def setUp(self):
        self.stone = Item(1, "minecraft:stone")
        self.pickaxe = Item(2, "minecraft:iron_pickaxe", max_stack_size=1, max_damage=250)
        self.inventory = Inventory()

    def test_default_layout(self):
        self.assertEqual(len(self.inventory), 36)
        self.assertEqual(self.inventory.hotbar_size, 9)
        self.assertEqual(len(self.inventory.armor), 4)
        self.assertTrue(self.inventory.offhand.is_empty)
        self.assertEqual(self.inventory.selected_hotbar_slot, 0)

    def test_hotbar_selection_and_selected_item(self):
        self.inventory.set_slot(2, ItemStack(self.stone, 8))
        self.inventory.select_hotbar_slot(2)
        self.assertEqual(self.inventory.selected_hotbar_slot, 2)
        self.assertEqual(self.inventory.selected_item.count, 8)
        with self.assertRaises(IndexError):
            self.inventory.select_hotbar_slot(9)

    def test_set_slot_owns_copy(self):
        source = ItemStack(self.stone, 5)
        self.inventory.set_slot(0, source)
        source.shrink(2)
        self.assertEqual(self.inventory.get_slot(0).count, 5)

    def test_set_slot_rejects_oversized_stack(self):
        with self.assertRaises(ValueError):
            self.inventory.set_slot(0, ItemStack(self.stone, 65))

    def test_swap_slots(self):
        self.inventory.set_slot(0, ItemStack(self.stone, 3))
        self.inventory.set_slot(1, ItemStack(self.pickaxe, 1))
        self.inventory.swap_slots(0, 1)
        self.assertIs(self.inventory.get_slot(0).item, self.pickaxe)
        self.assertIs(self.inventory.get_slot(1).item, self.stone)

    def test_insert_merges_before_empty_slots(self):
        self.inventory.set_slot(0, ItemStack(self.stone, 60))
        remainder = self.inventory.insert(ItemStack(self.stone, 10))
        self.assertEqual(self.inventory.get_slot(0).count, 64)
        self.assertEqual(self.inventory.get_slot(1).count, 6)
        self.assertTrue(remainder.is_empty)

    def test_insert_splits_across_slots(self):
        remainder = self.inventory.insert(ItemStack(self.stone, 130))
        self.assertEqual([self.inventory.get_slot(i).count for i in range(3)], [64, 64, 2])
        self.assertTrue(remainder.is_empty)

    def test_insert_returns_remainder_when_full(self):
        for i in range(36):
            self.inventory.set_slot(i, ItemStack(self.stone, 64))
        remainder = self.inventory.insert(ItemStack(self.stone, 7))
        self.assertEqual(remainder.count, 7)

    def test_add_item_does_not_mutate_source(self):
        source = ItemStack(self.stone, 12)
        self.assertTrue(self.inventory.add_item(source))
        self.assertEqual(source.count, 12)
        self.assertEqual(self.inventory.count_item(self.stone), 12)

    def test_remove_from_slot(self):
        self.inventory.set_slot(4, ItemStack(self.stone, 9))
        removed = self.inventory.remove_from_slot(4, 4)
        self.assertEqual(removed.count, 4)
        self.assertEqual(self.inventory.get_slot(4).count, 5)

    def test_count_item_by_metadata(self):
        dye = Item(3, "minecraft:dye", has_subtypes=True)
        self.inventory.set_slot(0, ItemStack(dye, 4, metadata=1))
        self.inventory.set_slot(1, ItemStack(dye, 7, metadata=2))
        self.assertEqual(self.inventory.count_item(dye), 11)
        self.assertEqual(self.inventory.count_item(dye, metadata=1), 4)

    def test_armor_slot_only_accepts_one(self):
        self.inventory.set_armor_slot(0, ItemStack(self.pickaxe, 1))
        self.assertIs(self.inventory.armor[0].item, self.pickaxe)
        with self.assertRaises(ValueError):
            self.inventory.set_armor_slot(0, ItemStack(self.stone, 2))

    def test_offhand_and_clear(self):
        self.inventory.set_offhand(ItemStack(self.stone, 16))
        self.inventory.set_slot(0, ItemStack(self.stone, 2))
        self.inventory.select_hotbar_slot(4)
        self.inventory.clear()
        self.assertTrue(self.inventory.offhand.is_empty)
        self.assertTrue(self.inventory.get_slot(0).is_empty)
        self.assertEqual(self.inventory.selected_hotbar_slot, 0)

    def test_invalid_inventory_sizes(self):
        with self.assertRaises(ValueError):
            Inventory(main_size=8, hotbar_size=9)
        with self.assertRaises(ValueError):
            Inventory(hotbar_size=0)


if __name__ == "__main__":
    unittest.main()
