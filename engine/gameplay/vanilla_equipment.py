"""Vanilla Java 1.12.2 sword and hoe item definitions and crafting recipes."""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping

from engine.gameplay.crafting import Ingredient, RecipeManager, ShapedRecipe
from engine.gameplay.items import Item, ItemStack


@dataclass(frozen=True)
class EquipmentStats:
    """Combat/tool attributes copied from the 1.12.2 material rules."""
    category: str
    material: str
    durability: int
    attack_damage: float
    attack_speed: float


_MATERIALS = {
    "wooden": (59, 0.0),
    "stone": (131, 1.0),
    "iron": (250, 2.0),
    "diamond": (1561, 3.0),
    "golden": (32, 0.0),
}
_SWORD_IDS = {
    "wooden": 268, "stone": 272, "iron": 267,
    "diamond": 276, "golden": 283,
}
_HOE_IDS = {
    "wooden": 290, "stone": 291, "iron": 292,
    "diamond": 293, "golden": 294,
}


def create_vanilla_equipment_items() -> tuple[dict[str, Item], dict[str, EquipmentStats]]:
    """Create all ten legacy sword/hoe items with verified 1.12.2 IDs."""
    items: dict[str, Item] = {}
    stats: dict[str, EquipmentStats] = {}
    for material, (durability, bonus_damage) in _MATERIALS.items():
        sword_name = f"{material}_sword"
        hoe_name = f"{material}_hoe"
        items[sword_name] = Item(
            _SWORD_IDS[material], f"minecraft:{sword_name}",
            max_stack_size=1, max_damage=durability,
        )
        items[hoe_name] = Item(
            _HOE_IDS[material], f"minecraft:{hoe_name}",
            max_stack_size=1, max_damage=durability,
        )
        stats[sword_name] = EquipmentStats(
            "sword", material, durability, 4.0 + bonus_damage, -2.4,
        )
        stats[hoe_name] = EquipmentStats(
            "hoe", material, durability, 1.0, -3.0,
        )
    return items, stats


def create_vanilla_equipment_recipes(
    equipment_items: Mapping[str, Item],
    ingredients: Mapping[str, Item],
) -> RecipeManager:
    """Create sword and hoe shaped recipes; patterns support mirroring."""
    required = {"planks", "cobblestone", "iron_ingot", "diamond", "gold_ingot", "stick"}
    missing = required - set(ingredients)
    if missing:
        raise ValueError(f"missing crafting ingredients: {sorted(missing)!r}")
    materials = {
        "wooden": Ingredient(ingredients["planks"]),
        "stone": Ingredient(ingredients["cobblestone"]),
        "iron": Ingredient(ingredients["iron_ingot"]),
        "diamond": Ingredient(ingredients["diamond"]),
        "golden": Ingredient(ingredients["gold_ingot"]),
    }
    stick = Ingredient(ingredients["stick"])
    recipes = RecipeManager()
    for material, ingredient in materials.items():
        sword = equipment_items.get(f"{material}_sword")
        if sword is not None:
            recipes.register(ShapedRecipe(
                1, 3, (ingredient, ingredient, stick), ItemStack(sword, 1),
            ))
        hoe = equipment_items.get(f"{material}_hoe")
        if hoe is not None:
            recipes.register(ShapedRecipe(
                2, 3,
                (ingredient, ingredient, stick, None, stick, None),
                ItemStack(hoe, 1),
            ))
    return recipes


__all__ = [
    "EquipmentStats", "create_vanilla_equipment_items",
    "create_vanilla_equipment_recipes",
]
