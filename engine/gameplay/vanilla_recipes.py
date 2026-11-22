"""Verified starter crafting recipes for the Minecraft Java 1.12.2 tool set."""
from __future__ import annotations

from engine.gameplay.crafting import Ingredient, RecipeManager, ShapedRecipe
from engine.gameplay.items import Item, ItemStack


def create_vanilla_tool_recipes(tool_items: dict[str, Item],
                                ingredient_items: dict[str, Item]) -> RecipeManager:
    required = {"planks", "cobblestone", "iron_ingot", "diamond", "gold_ingot", "stick"}
    missing = required - set(ingredient_items)
    if missing:
        raise ValueError(f"missing crafting ingredients: {sorted(missing)}")
    materials = {
        "wooden": Ingredient(ingredient_items["planks"]),
        "stone": Ingredient(ingredient_items["cobblestone"]),
        "iron": Ingredient(ingredient_items["iron_ingot"]),
        "diamond": Ingredient(ingredient_items["diamond"]),
        "golden": Ingredient(ingredient_items["gold_ingot"]),
    }
    stick = Ingredient(ingredient_items["stick"])
    manager = RecipeManager()
    for material, ingredient in materials.items():
        for tool_class in ("pickaxe", "axe", "shovel"):
            name = material + "_" + tool_class
            output_item = tool_items.get(name)
            if output_item is None:
                continue
            if tool_class == "pickaxe":
                pattern = (
                    ingredient, ingredient, ingredient,
                    None, stick, None,
                    None, stick, None,
                )
            elif tool_class == "axe":
                pattern = (
                    ingredient, ingredient, None,
                    ingredient, stick, None,
                    None, stick, None,
                )
            else:
                pattern = (
                    None, ingredient, None,
                    None, stick, None,
                    None, stick, None,
                )
            manager.register(ShapedRecipe(3, 3, pattern, ItemStack(output_item)))
    return manager


__all__ = ["create_vanilla_tool_recipes"]
