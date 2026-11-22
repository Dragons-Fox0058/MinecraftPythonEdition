"""Source-backed vanilla 1.12.2 armor definitions."""
from __future__ import annotations

from collections.abc import Mapping

from engine.gameplay.damage import ArmorDefinition, ArmorRegistry
from engine.gameplay.items import Item


# Durability multipliers by armor slot: boots, leggings, chestplate, helmet.
_ARMOR_SLOT_MULTIPLIERS = {
    "boots": 13,
    "leggings": 15,
    "chestplate": 16,
    "helmet": 11,
}

# (base durability, armor points by slot, toughness)
VANILLA_ARMOR_MATERIALS = {
    "leather": (5, {"boots": 1, "leggings": 2, "chestplate": 3, "helmet": 1}, 0.0),
    "chainmail": (15, {"boots": 1, "leggings": 4, "chestplate": 5, "helmet": 2}, 0.0),
    "iron": (15, {"boots": 2, "leggings": 5, "chestplate": 6, "helmet": 2}, 0.0),
    "golden": (7, {"boots": 1, "leggings": 3, "chestplate": 5, "helmet": 2}, 0.0),
    "diamond": (33, {"boots": 3, "leggings": 6, "chestplate": 8, "helmet": 3}, 2.0),
}


def create_vanilla_armor_registry(items: Mapping[str, Item]) -> ArmorRegistry:
    """Create armor rules for caller-supplied items without guessing legacy IDs.

    Keys use names such as diamond_helmet and iron_chestplate.
    Item durability must match the 1.12.2 material/slot durability.
    """
    if not isinstance(items, Mapping):
        raise TypeError("items must be a mapping of canonical names to Item")
    valid_keys = {
        f"{material}_{slot}"
        for material in VANILLA_ARMOR_MATERIALS
        for slot in _ARMOR_SLOT_MULTIPLIERS
    }
    unknown = set(items) - valid_keys
    if unknown:
        raise ValueError(f"unknown vanilla armor names: {sorted(unknown)!r}")

    registry = ArmorRegistry()
    for key, item in items.items():
        if not isinstance(item, Item):
            raise TypeError(f"{key} must map to an Item")
        material_name, slot = key.split("_", 1)
        base_durability, points, toughness = VANILLA_ARMOR_MATERIALS[material_name]
        expected_durability = base_durability * _ARMOR_SLOT_MULTIPLIERS[slot]
        if item.max_damage != expected_durability:
            raise ValueError(
                f"{key} max_damage must be {expected_durability}, got {item.max_damage}"
            )
        registry.register(ArmorDefinition(item, points[slot], toughness))
    return registry


__all__ = ["VANILLA_ARMOR_MATERIALS", "create_vanilla_armor_registry"]
