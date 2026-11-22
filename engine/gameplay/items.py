"""Item definitions, registry, and stack semantics for Minecraft 1.12.2."""
from __future__ import annotations

from copy import deepcopy
from typing import Any


class Item:
    """A registered item type. Numeric IDs must come from verified 1.12.2 data."""

    __slots__ = ("item_id", "name", "max_stack_size", "max_damage", "has_subtypes")

    def __init__(self, item_id: int, name: str, max_stack_size: int = 64,
                 max_damage: int = 0, has_subtypes: bool = False) -> None:
        if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 0:
            raise ValueError("item_id must be a non-negative integer")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        if isinstance(max_stack_size, bool) or not isinstance(max_stack_size, int):
            raise ValueError("max_stack_size must be an integer")
        if not 1 <= max_stack_size <= 64:
            raise ValueError("max_stack_size must be between 1 and 64")
        if isinstance(max_damage, bool) or not isinstance(max_damage, int) or max_damage < 0:
            raise ValueError("max_damage must be a non-negative integer")
        if max_damage and max_stack_size != 1:
            raise ValueError("damageable items must have max_stack_size=1")
        if not isinstance(has_subtypes, bool):
            raise ValueError("has_subtypes must be a bool")
        self.item_id = item_id
        self.name = name.strip()
        self.max_stack_size = max_stack_size
        self.max_damage = max_damage
        self.has_subtypes = has_subtypes

    @property
    def is_damageable(self) -> bool:
        return self.max_damage > 0

    def __repr__(self) -> str:
        return (f"Item(item_id={self.item_id!r}, name={self.name!r}, "
                f"max_stack_size={self.max_stack_size!r}, "
                f"max_damage={self.max_damage!r}, has_subtypes={self.has_subtypes!r})")


class ItemRegistry:
    """Two-way item registry with duplicate protection and optional freezing."""

    def __init__(self) -> None:
        self._by_id: dict[int, Item] = {}
        self._by_name: dict[str, Item] = {}
        self._frozen = False

    @property
    def frozen(self) -> bool:
        return self._frozen

    def register(self, item: Item) -> Item:
        if self._frozen:
            raise RuntimeError("item registry is frozen")
        if not isinstance(item, Item):
            raise TypeError("only Item instances can be registered")
        if item.item_id in self._by_id:
            raise ValueError(f"duplicate item ID: {item.item_id}")
        if item.name in self._by_name:
            raise ValueError(f"duplicate item name: {item.name}")
        self._by_id[item.item_id] = item
        self._by_name[item.name] = item
        return item

    def get_by_id(self, item_id: int) -> Item | None:
        return self._by_id.get(item_id)

    def get_by_name(self, name: str) -> Item | None:
        return self._by_name.get(name)

    def require_by_id(self, item_id: int) -> Item:
        item = self.get_by_id(item_id)
        if item is None:
            raise KeyError(f"unknown item ID: {item_id}")
        return item

    def require_by_name(self, name: str) -> Item:
        item = self.get_by_name(name)
        if item is None:
            raise KeyError(f"unknown item name: {name}")
        return item

    def freeze(self) -> None:
        self._frozen = True

    def __contains__(self, key: object) -> bool:
        if isinstance(key, int) and not isinstance(key, bool):
            return key in self._by_id
        if isinstance(key, str):
            return key in self._by_name
        if isinstance(key, Item):
            return self._by_id.get(key.item_id) is key
        return False

    def __len__(self) -> int:
        return len(self._by_id)

    def __iter__(self):
        return iter(self._by_id.values())

    def values(self) -> tuple[Item, ...]:
        return tuple(self._by_id.values())


class ItemStack:
    """Mutable stack; metadata, durability, and NBT are independent fields."""

    __slots__ = ("item", "count", "metadata", "damage", "nbt")

    def __init__(self, item: Item | None = None, count: int = 0, metadata: int = 0,
                 damage: int = 0, nbt: dict[str, Any] | None = None) -> None:
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("count must be a non-negative integer")
        if isinstance(metadata, bool) or not isinstance(metadata, int) or not 0 <= metadata <= 32767:
            raise ValueError("metadata must be an integer from 0 to 32767")
        if isinstance(damage, bool) or not isinstance(damage, int) or damage < 0:
            raise ValueError("damage must be a non-negative integer")
        if item is None:
            if count != 0 or metadata != 0 or damage != 0 or nbt:
                raise ValueError("an empty stack cannot contain item data")
        elif not isinstance(item, Item):
            raise TypeError("item must be an Item or None")
        elif count > 0 and damage > item.max_damage:
            raise ValueError("damage cannot exceed max_damage")
        if nbt is not None and not isinstance(nbt, dict):
            raise TypeError("nbt must be a dict or None")
        self.item = item if count else None
        self.count = count
        self.metadata = metadata if count else 0
        self.damage = damage if count else 0
        self.nbt = deepcopy(nbt) if count and nbt is not None else None

    @classmethod
    def empty(cls) -> "ItemStack":
        return cls()

    @property
    def is_empty(self) -> bool:
        return self.item is None or self.count <= 0

    @property
    def max_stack_size(self) -> int:
        return 0 if self.is_empty else self.item.max_stack_size

    def copy(self) -> "ItemStack":
        if self.is_empty:
            return ItemStack.empty()
        return ItemStack(self.item, self.count, self.metadata, self.damage, self.nbt)

    def _clear(self) -> None:
        self.item = None
        self.count = self.metadata = self.damage = 0
        self.nbt = None

    def split(self, amount: int) -> "ItemStack":
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValueError("amount must be a non-negative integer")
        if self.is_empty or amount == 0:
            return ItemStack.empty()
        taken = min(amount, self.count)
        result = ItemStack(self.item, taken, self.metadata, self.damage, self.nbt)
        self.shrink(taken)
        return result

    def shrink(self, amount: int) -> None:
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValueError("amount must be a non-negative integer")
        if self.is_empty or amount == 0:
            return
        self.count = max(0, self.count - amount)
        if self.count == 0:
            self._clear()

    def grow(self, amount: int) -> None:
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValueError("amount must be a non-negative integer")
        if self.is_empty:
            if amount:
                raise ValueError("cannot grow an empty stack")
            return
        if self.count + amount > self.item.max_stack_size:
            raise ValueError("growth would exceed max_stack_size")
        self.count += amount

    def can_stack_with(self, other: "ItemStack") -> bool:
        if not isinstance(other, ItemStack) or self.is_empty or other.is_empty:
            return False
        return (self.item is other.item and self.metadata == other.metadata
                and self.damage == other.damage and self.nbt == other.nbt
                and self.item.max_stack_size > 1)

    def merge_from(self, other: "ItemStack") -> int:
        """Transfer as many items as possible from other; return amount moved."""
        if not isinstance(other, ItemStack):
            raise TypeError("other must be an ItemStack")
        if other.is_empty:
            return 0
        if self.is_empty:
            moved = min(other.count, other.item.max_stack_size)
            self.item, self.count = other.item, moved
            self.metadata, self.damage = other.metadata, other.damage
            self.nbt = deepcopy(other.nbt)
            other.shrink(moved)
            return moved
        if not self.can_stack_with(other):
            return 0
        moved = min(other.count, self.item.max_stack_size - self.count)
        if moved:
            self.count += moved
            other.shrink(moved)
        return moved

    def damage_item(self, amount: int = 1) -> bool:
        """Apply durability damage and return True if the item broke."""
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValueError("amount must be a non-negative integer")
        if self.is_empty or not self.item.is_damageable or amount == 0:
            return False
        self.damage += amount
        if self.damage >= self.item.max_damage:
            self.shrink(1)
            return True
        return False

    def __bool__(self) -> bool:
        return not self.is_empty

    def __len__(self) -> int:
        return self.count

    def __repr__(self) -> str:
        if self.is_empty:
            return "ItemStack.empty()"
        return (f"ItemStack({self.item!r}, count={self.count}, metadata={self.metadata}, "
                f"damage={self.damage}, nbt={self.nbt!r})")


# Populated only when the vanilla catalogue has been verified against 1.12.2.
ITEM_REGISTRY = ItemRegistry()

__all__ = ["Item", "ItemRegistry", "ItemStack", "ITEM_REGISTRY"]
