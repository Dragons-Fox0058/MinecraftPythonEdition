"""Player inventory and hotbar for the Minecraft 1.12.2 target."""
from __future__ import annotations

from engine.gameplay.items import Item, ItemStack


class Inventory:
    """36 main slots (including a 9-slot hotbar), four armor slots, and offhand."""

    def __init__(self, main_size: int = 36, hotbar_size: int = 9, armor_size: int = 4) -> None:
        for label, value in (("main_size", main_size), ("hotbar_size", hotbar_size),
                             ("armor_size", armor_size)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{label} must be a non-negative integer")
        if hotbar_size > main_size:
            raise ValueError("hotbar_size cannot exceed main_size")
        if hotbar_size == 0:
            raise ValueError("hotbar_size must be at least 1")
        self.main_size = main_size
        self.hotbar_size = hotbar_size
        self.armor_size = armor_size
        self.slots = [ItemStack.empty() for _ in range(main_size)]
        self.armor = [ItemStack.empty() for _ in range(armor_size)]
        self.offhand = ItemStack.empty()
        self.selected_hotbar_slot = 0

    def _check_index(self, index: int, size: int, label: str) -> None:
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < size:
            raise IndexError(f"{label} index out of range: {index}")

    def get_slot(self, index: int) -> ItemStack:
        self._check_index(index, self.main_size, "inventory")
        return self.slots[index]

    def set_slot(self, index: int, stack: ItemStack) -> None:
        self._check_index(index, self.main_size, "inventory")
        if not isinstance(stack, ItemStack):
            raise TypeError("stack must be an ItemStack")
        if not stack.is_empty and stack.count > stack.item.max_stack_size:
            raise ValueError("stack exceeds its item's maximum stack size")
        self.slots[index] = stack.copy()

    def get_hotbar_slot(self, index: int) -> ItemStack:
        self._check_index(index, self.hotbar_size, "hotbar")
        return self.slots[index]

    def select_hotbar_slot(self, index: int) -> None:
        self._check_index(index, self.hotbar_size, "hotbar")
        self.selected_hotbar_slot = index

    @property
    def selected_item(self) -> ItemStack:
        return self.slots[self.selected_hotbar_slot]

    def swap_slots(self, first: int, second: int) -> None:
        self._check_index(first, self.main_size, "inventory")
        self._check_index(second, self.main_size, "inventory")
        self.slots[first], self.slots[second] = self.slots[second], self.slots[first]

    def set_armor_slot(self, index: int, stack: ItemStack) -> None:
        self._check_index(index, self.armor_size, "armor")
        if not isinstance(stack, ItemStack):
            raise TypeError("stack must be an ItemStack")
        if not stack.is_empty and stack.count != 1:
            raise ValueError("an armor slot can contain only one item")
        self.armor[index] = stack.copy()

    def set_offhand(self, stack: ItemStack) -> None:
        if not isinstance(stack, ItemStack):
            raise TypeError("stack must be an ItemStack")
        if not stack.is_empty and stack.count > stack.item.max_stack_size:
            raise ValueError("stack exceeds its item's maximum stack size")
        self.offhand = stack.copy()

    def insert(self, stack: ItemStack) -> ItemStack:
        """Insert into existing stacks then empty slots; return the remainder.

        The supplied stack is not modified. Inventory owns independent copies.
        """
        if not isinstance(stack, ItemStack):
            raise TypeError("stack must be an ItemStack")
        remainder = stack.copy()
        if remainder.is_empty:
            return remainder

        for current in self.slots:
            if current.can_stack_with(remainder):
                current.merge_from(remainder)
                if remainder.is_empty:
                    return remainder

        while not remainder.is_empty:
            empty_index = next(
                (i for i, current in enumerate(self.slots) if current.is_empty), None
            )
            if empty_index is None:
                break
            amount = min(remainder.count, remainder.item.max_stack_size)
            self.slots[empty_index] = remainder.split(amount)
        return remainder

    def add_item(self, stack: ItemStack) -> bool:
        """Insert a copy of stack and return True only when all items fit."""
        return self.insert(stack).is_empty

    def remove_from_slot(self, index: int, amount: int = 1) -> ItemStack:
        self._check_index(index, self.main_size, "inventory")
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValueError("amount must be a non-negative integer")
        return self.slots[index].split(amount)

    def count_item(self, item: Item, metadata: int | None = None) -> int:
        if not isinstance(item, Item):
            raise TypeError("item must be an Item")
        total = 0
        for stack in self.slots:
            if not stack.is_empty and stack.item is item:
                if metadata is None or stack.metadata == metadata:
                    total += stack.count
        return total

    def clear(self) -> None:
        for index in range(self.main_size):
            self.slots[index] = ItemStack.empty()
        for index in range(self.armor_size):
            self.armor[index] = ItemStack.empty()
        self.offhand = ItemStack.empty()
        self.selected_hotbar_slot = 0

    def __len__(self) -> int:
        return self.main_size


__all__ = ["Inventory"]
