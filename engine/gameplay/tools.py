"""Tool material, effectiveness, and harvest-level rules for gameplay."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping

from engine.gameplay.items import Item


@dataclass(frozen=True)
class ToolMaterial:
    name: str
    durability: int
    efficiency: float
    harvest_level: int
    enchantability: int = 0
    damage_vs_entity: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("material name must be non-empty")
        if isinstance(self.durability, bool) or not isinstance(self.durability, int) or self.durability <= 0:
            raise ValueError("durability must be a positive integer")
        if isinstance(self.efficiency, bool) or not isinstance(self.efficiency, (int, float)) or self.efficiency <= 0:
            raise ValueError("efficiency must be positive")
        if isinstance(self.harvest_level, bool) or not isinstance(self.harvest_level, int) or self.harvest_level < 0:
            raise ValueError("harvest_level must be a non-negative integer")
        if isinstance(self.enchantability, bool) or not isinstance(self.enchantability, int) or self.enchantability < 0:
            raise ValueError("enchantability must be a non-negative integer")
        if (isinstance(self.damage_vs_entity, bool)
                or not isinstance(self.damage_vs_entity, (int, float))
                or self.damage_vs_entity < 0):
            raise ValueError("damage_vs_entity must be non-negative")


@dataclass(frozen=True)
class ToolDefinition:
    item: Item
    tool_class: str
    material: ToolMaterial
    effective_blocks: frozenset[str]

    def __post_init__(self) -> None:
        if not isinstance(self.item, Item):
            raise TypeError("item must be an Item")
        if not self.item.is_damageable:
            raise ValueError("tool item must be damageable")
        if not isinstance(self.tool_class, str) or not self.tool_class:
            raise ValueError("tool_class must be non-empty")
        if not isinstance(self.material, ToolMaterial):
            raise TypeError("material must be ToolMaterial")
        if self.item.max_damage != self.material.durability:
            raise ValueError("item max_damage must match material durability")
        if any(not isinstance(name, str) or not name for name in self.effective_blocks):
            raise ValueError("effective block names must be non-empty strings")


class ToolRegistry:
    """Explicit item-to-tool and block-to-harvest-requirement mappings.

    The registry deliberately does not guess block effectiveness from material
    names. Populate it from verified 1.12.2 block/tool data.
    """

    def __init__(self) -> None:
        self._tools: dict[Item, ToolDefinition] = {}
        self._requirements: dict[str, tuple[str, int]] = {}

    def register(self, definition: ToolDefinition) -> ToolDefinition:
        if not isinstance(definition, ToolDefinition):
            raise TypeError("definition must be a ToolDefinition")
        if definition.item in self._tools:
            raise ValueError(f"tool already registered: {definition.item.name}")
        self._tools[definition.item] = definition
        return definition

    def set_harvest_requirement(self, block_name: str, tool_class: str, level: int) -> None:
        if not isinstance(block_name, str) or not block_name:
            raise ValueError("block_name must be non-empty")
        if not isinstance(tool_class, str) or not tool_class:
            raise ValueError("tool_class must be non-empty")
        if isinstance(level, bool) or not isinstance(level, int) or level < 0:
            raise ValueError("harvest level must be a non-negative integer")
        if block_name in self._requirements:
            raise ValueError(f"harvest requirement already registered: {block_name}")
        self._requirements[block_name] = (tool_class, level)

    def get(self, item: Item | None) -> ToolDefinition | None:
        return self._tools.get(item)

    def dig_speed(self, item: Item | None, block_name: str) -> float:
        definition = self.get(item)
        if definition is None or block_name not in definition.effective_blocks:
            return 1.0
        return float(definition.material.efficiency)

    def can_harvest(self, item: Item | None, block_name: str) -> bool:
        requirement = self._requirements.get(block_name)
        if requirement is None:
            return True
        definition = self.get(item)
        if definition is None:
            return False
        required_class, required_level = requirement
        return (definition.tool_class == required_class
                and definition.material.harvest_level >= required_level)

    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(self._tools.values())

    def requirements(self) -> Mapping[str, tuple[str, int]]:
        return MappingProxyType(self._requirements)


__all__ = ["ToolMaterial", "ToolDefinition", "ToolRegistry"]