"""Tests for Phase 6 item definitions, registry, and stack behavior."""
import unittest

from engine.gameplay import ITEM_REGISTRY, Item, ItemRegistry, ItemStack


class TestItem(unittest.TestCase):
    def test_item_properties(self):
        item = Item(1, "minecraft:stone")
        self.assertEqual(item.item_id, 1)
        self.assertEqual(item.name, "minecraft:stone")
        self.assertEqual(item.max_stack_size, 64)
        self.assertFalse(item.is_damageable)

    def test_item_can_define_container_item(self):
        bucket = Item(325, "minecraft:bucket", max_stack_size=16)
        milk_bucket = Item(335, "minecraft:milk_bucket", max_stack_size=1,
                           container_item=bucket)
        self.assertIs(milk_bucket.container_item, bucket)
        self.assertEqual(milk_bucket.container_item_metadata, 0)

    def test_damageable_item_must_not_stack(self):
        with self.assertRaises(ValueError):
            Item(2, "minecraft:pickaxe", max_stack_size=64, max_damage=250)
        pick = Item(2, "minecraft:pickaxe", max_stack_size=1, max_damage=250)
        self.assertTrue(pick.is_damageable)

    def test_invalid_item_values(self):
        for args in ((-1, "x"), (1, ""), (1, "x", 0), (1, "x", 65), (1, "x", 64, -1)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                Item(*args)


class TestItemRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = ItemRegistry()
        self.stone = Item(1, "minecraft:stone")
        self.registry.register(self.stone)

    def test_lookup_by_id_and_name(self):
        self.assertIs(self.registry.get_by_id(1), self.stone)
        self.assertIs(self.registry.get_by_name("minecraft:stone"), self.stone)
        self.assertIs(self.registry.require_by_id(1), self.stone)
        self.assertIs(self.registry.require_by_name("minecraft:stone"), self.stone)
        self.assertEqual(len(self.registry), 1)
        self.assertIn(1, self.registry)
        self.assertIn("minecraft:stone", self.registry)
        self.assertIn(self.stone, self.registry)

    def test_unknown_required_lookup(self):
        with self.assertRaises(KeyError):
            self.registry.require_by_id(999)
        with self.assertRaises(KeyError):
            self.registry.require_by_name("missing")

    def test_duplicate_id_and_name_rejected(self):
        with self.assertRaises(ValueError):
            self.registry.register(Item(1, "minecraft:dirt"))
        with self.assertRaises(ValueError):
            self.registry.register(Item(2, "minecraft:stone"))

    def test_freeze_prevents_registration(self):
        self.registry.freeze()
        self.assertTrue(self.registry.frozen)
        with self.assertRaises(RuntimeError):
            self.registry.register(Item(2, "minecraft:dirt"))

    def test_non_item_rejected(self):
        with self.assertRaises(TypeError):
            self.registry.register(object())


class TestItemStack(unittest.TestCase):
    def setUp(self):
        self.stone = Item(1, "minecraft:stone")
        self.dye = Item(2, "minecraft:dye", has_subtypes=True)
        self.pickaxe = Item(3, "minecraft:iron_pickaxe", max_stack_size=1, max_damage=250)

    def test_empty_stack(self):
        stack = ItemStack.empty()
        self.assertTrue(stack.is_empty)
        self.assertFalse(stack)
        self.assertEqual(len(stack), 0)

    def test_constructor_and_validation(self):
        stack = ItemStack(self.stone, 12)
        self.assertEqual(stack.count, 12)
        with self.assertRaises(ValueError):
            ItemStack(self.stone, -1)
        with self.assertRaises(ValueError):
            ItemStack(None, 1)
        with self.assertRaises(ValueError):
            ItemStack(self.dye, 1, metadata=32768)

    def test_copy_is_independent_including_nbt(self):
        original = ItemStack(self.stone, 4, nbt={"display": {"name": "Test"}})
        clone = original.copy()
        clone.nbt["display"]["name"] = "Changed"
        clone.shrink(1)
        self.assertEqual(original.count, 4)
        self.assertEqual(original.nbt["display"]["name"], "Test")

    def test_split_preserves_stack_data(self):
        stack = ItemStack(self.dye, 10, metadata=5, nbt={"tag": [1, 2]})
        part = stack.split(3)
        self.assertEqual(part.count, 3)
        self.assertEqual(stack.count, 7)
        self.assertEqual(part.metadata, 5)
        self.assertEqual(part.nbt, {"tag": [1, 2]})

    def test_split_all_clears_source(self):
        stack = ItemStack(self.stone, 3)
        part = stack.split(10)
        self.assertEqual(part.count, 3)
        self.assertTrue(stack.is_empty)

    def test_shrink_and_grow(self):
        stack = ItemStack(self.stone, 60)
        stack.grow(4)
        self.assertEqual(stack.count, 64)
        with self.assertRaises(ValueError):
            stack.grow(1)
        stack.shrink(64)
        self.assertTrue(stack.is_empty)

    def test_empty_stack_cannot_grow(self):
        with self.assertRaises(ValueError):
            ItemStack.empty().grow(1)

    def test_stacking_requires_same_item_and_data(self):
        self.assertTrue(ItemStack(self.stone, 2).can_stack_with(ItemStack(self.stone, 3)))
        self.assertFalse(ItemStack(self.dye, 2, metadata=1).can_stack_with(ItemStack(self.dye, 3, metadata=2)))
        self.assertFalse(ItemStack(self.stone, 2).can_stack_with(ItemStack(self.dye, 2)))
        self.assertFalse(ItemStack(self.pickaxe, 1).can_stack_with(ItemStack(self.pickaxe, 1)))

    def test_merge_respects_stack_limit(self):
        target = ItemStack(self.stone, 60)
        source = ItemStack(self.stone, 10)
        moved = target.merge_from(source)
        self.assertEqual(moved, 4)
        self.assertEqual(target.count, 64)
        self.assertEqual(source.count, 6)

    def test_merge_into_empty_stack(self):
        target = ItemStack.empty()
        source = ItemStack(self.stone, 70)
        moved = target.merge_from(source)
        self.assertEqual(moved, 64)
        self.assertEqual(target.count, 64)
        self.assertEqual(source.count, 6)

    def test_merge_does_not_merge_different_metadata(self):
        target = ItemStack(self.dye, 2, metadata=1)
        source = ItemStack(self.dye, 2, metadata=2)
        self.assertEqual(target.merge_from(source), 0)
        self.assertEqual(source.count, 2)

    def test_merge_does_not_merge_different_nbt(self):
        target = ItemStack(self.stone, 2, nbt={"a": 1})
        source = ItemStack(self.stone, 2, nbt={"a": 2})
        self.assertEqual(target.merge_from(source), 0)

    def test_damageable_stack_breaks_at_max_damage(self):
        stack = ItemStack(self.pickaxe, 1, damage=249)
        self.assertTrue(stack.damage_item(1))
        self.assertTrue(stack.is_empty)

    def test_damageable_stack_keeps_damage_before_break(self):
        stack = ItemStack(self.pickaxe, 1)
        self.assertFalse(stack.damage_item(10))
        self.assertEqual(stack.damage, 10)

    def test_global_registry_is_available_and_initially_empty(self):
        self.assertIsInstance(ITEM_REGISTRY, ItemRegistry)


if __name__ == "__main__":
    unittest.main()
