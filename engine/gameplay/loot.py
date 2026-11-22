"""Data-driven block loot tables with deterministic random selection."""
from __future__ import annotations

import random
from dataclasses import dataclass
from collections.abc import Iterable, Mapping

from engine.gameplay.items import Item, ItemStack


@dataclass(frozen=True)
class LootEntry:
    item: Item
    min_count: int = 1
    max_count: int = 1
    weight: int = 1
    requires_harvest: bool = True
    metadata: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.item, Item):
            raise TypeError("loot item must be an Item")
        for name, value, minimum in (
            ("min_count", self.min_count, 0),
            ("max_count", self.max_count, 0),
            ("weight", self.weight, 1),
            ("metadata", self.metadata, 0),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f"{name} is invalid")
        if self.max_count < self.min_count or self.max_count > self.item.max_stack_size:
            raise ValueError("loot count range is incompatible with item stack size")
        if self.metadata > 32767:
            raise ValueError("metadata must be <= 32767")
        if not isinstance(self.requires_harvest, bool):
            raise TypeError("requires_harvest must be bool")


@dataclass(frozen=True)
class BlockLootTable:
    entries: tuple[LootEntry, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.entries, tuple) or not self.entries:
            raise ValueError("loot table must contain a non-empty tuple of entries")
        if any(not isinstance(entry, LootEntry) for entry in self.entries):
            raise TypeError("entries must contain LootEntry values")

    def generate(self, can_harvest: bool, rng: random.Random) -> tuple[ItemStack, ...]:
        if not isinstance(can_harvest, bool):
            raise TypeError("can_harvest must be bool")
        if not isinstance(rng, random.Random):
            raise TypeError("rng must be random.Random")
        eligible = [entry for entry in self.entries
                    if can_harvest or not entry.requires_harvest]
        if not eligible:
            return ()
        total = sum(entry.weight for entry in eligible)
        choice = rng.randrange(total)
        selected = eligible[-1]
        for entry in eligible:
            if choice < entry.weight:
                selected = entry
                break
            choice -= entry.weight
        count = rng.randint(selected.min_count, selected.max_count)
        if count <= 0:
            return ()
        result = []
        while count:
            amount = min(count, selected.item.max_stack_size)
            result.append(ItemStack(selected.item, amount, metadata=selected.metadata))
            count -= amount
        return tuple(result)


class LootTableRegistry:
    def __init__(self) -> None:
        self._tables: dict[str, BlockLootTable] = {}

    def register(self, block_name: str, table: BlockLootTable) -> None:
        if not isinstance(block_name, str) or not block_name:
            raise ValueError("block_name must be non-empty")
        if not isinstance(table, BlockLootTable):
            raise TypeError("table must be BlockLootTable")
        if block_name in self._tables:
            raise ValueError(f"loot table already registered: {block_name}")
        self._tables[block_name] = table

    def get(self, block_name: str) -> BlockLootTable | None:
        return self._tables.get(block_name)

    def generate(self, block_name: str, can_harvest: bool,
                 rng: random.Random | None = None) -> tuple[ItemStack, ...]:
        table = self.get(block_name)
        if table is None:
            return ()
        return table.generate(can_harvest, rng if rng is not None else random.Random())


__all__ = ["LootEntry", "BlockLootTable", "LootTableRegistry"]
