"""Damage sources and armor reduction for Minecraft Java 1.12.2."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from engine.gameplay.items import Item, ItemStack


@dataclass(frozen=True)
class DamageSource:
    """Describes how damage is applied and which defenses it bypasses."""

    name: str
    bypasses_armor: bool = False
    absolute: bool = False
    fire: bool = False
    magic: bool = False
    explosion: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("damage source name must be non-empty")
        for field_name in (
            "bypasses_armor", "absolute", "fire", "magic", "explosion"
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be a bool")

    @property
    def ignores_armor(self) -> bool:
        return self.bypasses_armor or self.absolute or self.magic


@dataclass(frozen=True)
class ArmorDefinition:
    item: Item
    armor_points: int
    toughness: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.item, Item):
            raise TypeError("item must be an Item")
        if isinstance(self.armor_points, bool) or not isinstance(self.armor_points, int):
            raise TypeError("armor_points must be an integer")
        if not 0 <= self.armor_points <= 20:
            raise ValueError("armor_points must be from 0 to 20")
        if (isinstance(self.toughness, bool)
                or not isinstance(self.toughness, (int, float))
                or not math.isfinite(self.toughness) or self.toughness < 0):
            raise ValueError("toughness must be finite and non-negative")


class ArmorRegistry:
    """Explicit armor-item definitions; item IDs are supplied by the catalogue."""

    def __init__(self) -> None:
        self._definitions: dict[Item, ArmorDefinition] = {}

    def register(self, definition: ArmorDefinition) -> ArmorDefinition:
        if not isinstance(definition, ArmorDefinition):
            raise TypeError("definition must be an ArmorDefinition")
        if definition.item in self._definitions:
            raise ValueError(f"armor already registered: {definition.item.name}")
        if not definition.item.is_damageable:
            raise ValueError("armor item must be damageable")
        self._definitions[definition.item] = definition
        return definition

    def get(self, item: Item | None) -> ArmorDefinition | None:
        return self._definitions.get(item)

    def calculate_damage(
        self,
        amount: float,
        armor_stacks: Iterable[ItemStack],
        source: DamageSource,
    ) -> float:
        """Apply the 1.12.2 armor/toughness reduction formula."""
        if (isinstance(amount, bool) or not isinstance(amount, (int, float))
                or not math.isfinite(amount) or amount < 0):
            raise ValueError("amount must be finite and non-negative")
        if not isinstance(source, DamageSource):
            raise TypeError("source must be a DamageSource")
        stacks = tuple(armor_stacks)
        if any(not isinstance(stack, ItemStack) for stack in stacks):
            raise TypeError("armor_stacks must contain ItemStack values")
        if amount == 0 or source.ignores_armor:
            return float(amount)

        armor = 0
        toughness = 0.0
        for stack in stacks:
            if stack.is_empty:
                continue
            definition = self.get(stack.item)
            if definition is not None:
                armor += definition.armor_points
                toughness += definition.toughness

        reduction = min(
            20.0,
            max(armor / 5.0, armor - amount / (2.0 + toughness / 4.0)),
        )
        return float(amount) * (1.0 - reduction / 25.0)

    def damage_armor(
        self,
        amount: float,
        armor_stacks: Iterable[ItemStack],
        source: DamageSource,
    ) -> int:
        """Damage equipped armor and return the number of pieces broken."""
        if (isinstance(amount, bool) or not isinstance(amount, (int, float))
                or not math.isfinite(amount) or amount < 0):
            raise ValueError("amount must be finite and non-negative")
        if not isinstance(source, DamageSource):
            raise TypeError("source must be a DamageSource")
        if amount <= 0 or source.ignores_armor:
            return 0
        durability_damage = max(1, math.ceil(amount / 4.0))
        broken = 0
        for stack in tuple(armor_stacks):
            if not isinstance(stack, ItemStack):
                raise TypeError("armor_stacks must contain ItemStack values")
            if stack.is_empty or self.get(stack.item) is None:
                continue
            if stack.damage_item(durability_damage):
                broken += 1
        return broken


__all__ = ["DamageSource", "ArmorDefinition", "ArmorRegistry"]
