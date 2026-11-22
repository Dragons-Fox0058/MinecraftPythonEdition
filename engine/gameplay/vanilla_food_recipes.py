"""Safe vanilla food crafting recipes from the Minecraft Java 1.12.2 assets."""
from __future__ import annotations

from engine.gameplay.crafting import (
    CraftingGrid, Ingredient, RecipeManager, ShapedRecipe, ShapelessRecipe,
)
from engine.gameplay.items import ITEM_REGISTRY, Item, ItemRegistry, ItemStack
from engine.gameplay.vanilla_foods import register_vanilla_food_items
from engine.gameplay.vanilla_fuels import register_vanilla_fuel_items


def register_vanilla_food_recipe_items(
    registry: ItemRegistry = ITEM_REGISTRY,
) -> dict[str, Item]:
    """Register only the ingredients and outputs used by food recipes."""
    if not isinstance(registry, ItemRegistry):
        raise TypeError("registry must be an ItemRegistry")
    items = register_vanilla_food_items(registry)
    fuel_items = register_vanilla_fuel_items(registry)
    items.update(fuel_items)

    definitions = (
        (39, "minecraft:red_mushroom", 64, False, None),
        (40, "minecraft:brown_mushroom", 64, False, None),
        (86, "minecraft:pumpkin", 64, False, None),
        (296, "minecraft:wheat", 64, False, None),
        (335, "minecraft:milk_bucket", 1, False, "minecraft:bucket"),
        (344, "minecraft:egg", 16, False, None),
        (351, "minecraft:dye", 64, True, None),
        (353, "minecraft:sugar", 64, False, None),
        (354, "minecraft:cake", 1, False, None),
    )
    for item_id, name, stack_size, subtypes, container_name in definitions:
        existing_id = registry.get_by_id(item_id)
        existing_name = registry.get_by_name(name)
        if existing_id is not None or existing_name is not None:
            if existing_id is None or existing_name is not existing_id:
                raise ValueError(f"conflicting item registry entry for {name} ({item_id})")
            if existing_id.max_stack_size != stack_size:
                raise ValueError(f"incompatible stack size for existing item {name}")
            item = existing_id
            if subtypes:
                item.has_subtypes = True
        else:
            container = registry.get_by_name(container_name) if container_name else None
            item = Item(
                item_id, name, max_stack_size=stack_size,
                has_subtypes=subtypes, container_item=container,
            )
            registry.register(item)
        items[name] = item

    milk_bucket = items["minecraft:milk_bucket"]
    bucket = items["minecraft:bucket"]
    if milk_bucket.container_item is None:
        milk_bucket.container_item = bucket
    elif milk_bucket.container_item is not bucket:
        raise ValueError("incompatible milk bucket container item")
    return items


def register_vanilla_food_recipes(
    item_registry: ItemRegistry = ITEM_REGISTRY,
    recipe_manager: RecipeManager | None = None,
) -> RecipeManager:
    """Register source-backed 1.12.2 food recipes (not combat/weapon recipes)."""
    items = register_vanilla_food_recipe_items(item_registry)
    recipes = recipe_manager if recipe_manager is not None else RecipeManager()

    def item(name: str) -> Item:
        return items[name]

    recipes.register(ShapedRecipe(
        3, 1,
        [Ingredient(item("minecraft:wheat"))] * 3,
        ItemStack(item("minecraft:bread"), 1),
    ))
    recipes.register(ShapedRecipe(
        3, 1,
        [
            Ingredient(item("minecraft:wheat")),
            Ingredient(item("minecraft:dye"), metadata=3),
            Ingredient(item("minecraft:wheat")),
        ],
        ItemStack(item("minecraft:cookie"), 8),
    ))
    recipes.register(ShapedRecipe(
        3, 3,
        [
            Ingredient(item("minecraft:milk_bucket")),
            Ingredient(item("minecraft:milk_bucket")),
            Ingredient(item("minecraft:milk_bucket")),
            Ingredient(item("minecraft:sugar")),
            Ingredient(item("minecraft:egg")),
            Ingredient(item("minecraft:sugar")),
            Ingredient(item("minecraft:wheat")),
            Ingredient(item("minecraft:wheat")),
            Ingredient(item("minecraft:wheat")),
        ],
        ItemStack(item("minecraft:cake"), 1),
    ))
    recipes.register(ShapelessRecipe(
        [
            Ingredient(item("minecraft:pumpkin")),
            Ingredient(item("minecraft:sugar")),
            Ingredient(item("minecraft:egg")),
        ],
        ItemStack(item("minecraft:pumpkin_pie"), 1),
    ))
    recipes.register(ShapelessRecipe(
        [
            Ingredient(item("minecraft:brown_mushroom")),
            Ingredient(item("minecraft:red_mushroom")),
            Ingredient(item("minecraft:bowl")),
        ],
        ItemStack(item("minecraft:mushroom_stew"), 1),
    ))
    recipes.register(ShapedRecipe(
        3, 3,
        [
            Ingredient(item("minecraft:beetroot")),
            Ingredient(item("minecraft:beetroot")),
            Ingredient(item("minecraft:beetroot")),
            Ingredient(item("minecraft:beetroot")),
            Ingredient(item("minecraft:beetroot")),
            Ingredient(item("minecraft:beetroot")),
            None,
            Ingredient(item("minecraft:bowl")),
            None,
        ],
        ItemStack(item("minecraft:beetroot_soup"), 1),
    ))
    return recipes


__all__ = ["register_vanilla_food_recipe_items", "register_vanilla_food_recipes"]
